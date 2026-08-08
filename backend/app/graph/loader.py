from neo4j import Driver


def load_file_graph(driver: Driver, repo_full_name: str, edges: list[tuple[str, str]]) -> None:
    """
    Loads File nodes and IMPORTS edges into Neo4j.

    Uses MERGE instead of CREATE throughout, which makes this idempotent --
    running it again with the same data won't create duplicate nodes or
    edges. This is the same idempotency principle as the Postgres
    ingestion pipeline (ON CONFLICT DO NOTHING), just expressed in
    Cypher's own idiom instead of SQL's.

    File paths are namespaced by repo_full_name in each node, so ingesting
    a second repo later won't collide with this one's files.
    """
    with driver.session() as session:
        for from_file, to_file in edges:
            session.run(
                """
                MERGE (a:File {repo: $repo, path: $from_path})
                MERGE (b:File {repo: $repo, path: $to_path})
                MERGE (a)-[:IMPORTS]->(b)
                """,
                repo=repo_full_name,
                from_path=from_file,
                to_path=to_file,
            )


def count_graph(driver: Driver, repo_full_name: str) -> dict:
    """
    Quick sanity check query -- counts what's actually stored in Neo4j
    for this repo, so we can confirm the load worked without eyeballing
    the Neo4j Browser by hand.
    """
    with driver.session() as session:
        result = session.run(
            """
            MATCH (f:File {repo: $repo})
            OPTIONAL MATCH (f)-[r:IMPORTS]->()
            RETURN count(DISTINCT f) AS file_count, count(r) AS edge_count
            """,
            repo=repo_full_name,
        )
        record = result.single()
        return {"files": record["file_count"], "edges": record["edge_count"]}