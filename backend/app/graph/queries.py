from neo4j import Driver


def get_blast_radius(driver: Driver, repo_full_name: str, file_path: str, max_hops: int = 3) -> list[str]:
    """
    Finds every file that (directly or transitively) imports the given
    file -- i.e. "if this file breaks, what else might be affected."

    This walks IMPORTS edges *backwards*, from dependents toward the
    target file, up to max_hops away -- that's the direction that
    actually answers the blast-radius question (we want files that
    depend on this one, not files this one depends on).

    max_hops is baked directly into the query text rather than passed as
    a normal parameter, because Cypher's variable-length path syntax
    doesn't support parameterizing the hop range. Safe here since
    max_hops always comes from our own code as a real int, never from
    raw user input -- if this were ever exposed to user input directly,
    it would need validation first to avoid query injection.
    """
    with driver.session() as session:
        result = session.run(
            f"""
            MATCH (start:File {{repo: $repo, path: $path}})
            MATCH (dependent:File)-[:IMPORTS*1..{max_hops}]->(start)
            RETURN DISTINCT dependent.path AS path
            """,
            repo=repo_full_name,
            path=file_path,
        )
        return [record["path"] for record in result]


def get_recent_changes_near(
    driver: Driver, repo_full_name: str, file_path: str, max_hops: int = 1
) -> list[dict]:
    """
    Finds commits that touched the given file, or files within max_hops
    of it via IMPORTS, along with each commit's message and author.
    This is the "what changed recently near this code" signal that
    traversal will lean on heavily once ranking is built.
    """
    with driver.session() as session:
        result = session.run(
            f"""
            MATCH (start:File {{repo: $repo, path: $path}})
            MATCH (nearby:File)-[:IMPORTS*0..{max_hops}]-(start)
            MATCH (p:Person)-[:AUTHORED]->(c:Commit)-[:MODIFIES]->(nearby)
            RETURN DISTINCT c.sha AS sha, c.message AS message, p.name AS author, nearby.path AS file
            LIMIT 20
            """,
            repo=repo_full_name,
            path=file_path,
        )
        return [dict(record) for record in result]


def get_owner(driver: Driver, repo_full_name: str, file_path: str) -> dict | None:
    """
    Returns the derived owner of a file and how many edits back that up.
    Returns None if the file has no OWNED_BY relationship yet -- e.g. it
    wasn't touched by any of the bounded set of commits we've loaded so far.
    """
    with driver.session() as session:
        result = session.run(
            """
            MATCH (f:File {repo: $repo, path: $path})-[o:OWNED_BY]->(p:Person)
            RETURN p.name AS owner, o.edits AS edits
            """,
            repo=repo_full_name,
            path=file_path,
        )
        record = result.single()
        return dict(record) if record else None