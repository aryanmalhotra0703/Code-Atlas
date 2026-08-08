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


def load_commit_graph(driver: Driver, repo_full_name: str, commit_details: list[dict]) -> None:
    """
    Loads Person and Commit nodes, plus AUTHORED (Person -> Commit) and
    MODIFIES (Commit -> File) relationships, from full commit detail
    objects (which include each commit's list of changed files).
    """
    with driver.session() as session:
        for commit in commit_details:
            sha = commit["sha"]
            commit_info = commit.get("commit", {})
            author_info = commit_info.get("author") or {}
            author_name = author_info.get("name") or "unknown"
            full_message = commit_info.get("message") or ""
            message = full_message.splitlines()[0] if full_message else ""

            session.run(
                """
                MERGE (p:Person {name: $author_name})
                MERGE (c:Commit {repo: $repo, sha: $sha})
                SET c.message = $message
                MERGE (p)-[:AUTHORED]->(c)
                """,
                repo=repo_full_name,
                sha=sha,
                author_name=author_name,
                message=message,
            )

            for f in commit.get("files", []):
                session.run(
                    """
                    MATCH (c:Commit {repo: $repo, sha: $sha})
                    MERGE (file:File {repo: $repo, path: $path})
                    MERGE (c)-[:MODIFIES]->(file)
                    """,
                    repo=repo_full_name,
                    sha=sha,
                    path=f["filename"],
                )


def derive_ownership(driver: Driver, repo_full_name: str) -> None:
    """
    Derives an OWNED_BY relationship per file: the person who has
    modified it the most times, based on the MODIFIES/AUTHORED edges
    already in the graph.

    This is a heuristic, not a fact GitHub hands us directly. A different
    reasonable definition of "ownership" (most recent modifier, or a
    CODEOWNERS file) would give different results -- commit-frequency is
    simple, explainable, and good enough for a first pass, but it's worth
    being explicit that this is a design choice, not ground truth.
    """
    with driver.session() as session:
        session.run(
            """
            MATCH (p:Person)-[:AUTHORED]->(c:Commit {repo: $repo})-[:MODIFIES]->(f:File {repo: $repo})
            WITH f, p, count(*) AS edits
            ORDER BY edits DESC
            WITH f, collect({person: p, edits: edits})[0] AS top
            WITH f, top.person AS owner, top.edits AS edit_count
            MERGE (f)-[r:OWNED_BY]->(owner)
            SET r.edits = edit_count
            """,
            repo=repo_full_name,
        )