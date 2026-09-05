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

def get_files_for_commit(driver: Driver, repo_full_name: str, sha: str) -> list[str]:
    """
    Given a commit's sha, returns every file it touched -- this is the
    bridge between retrieval (which finds relevant commits/PRs by
    meaning) and traversal (which answers questions about files). A
    retrieved commit becomes a real starting point in the graph via
    exactly this lookup.
    """
    with driver.session() as session:
        result = session.run(
            """
            MATCH (c:Commit {repo: $repo, sha: $sha})-[:MODIFIES]->(f:File)
            RETURN f.path AS path
            """,
            repo=repo_full_name,
            sha=sha,
        )
        return [record["path"] for record in result]

def get_commits_for_pr(driver: Driver, repo_full_name: str, pr_number: str) -> list[str]:
    """
    Given a PR number, returns the shas of commits it contains -- the
    bridge that lets a retrieved PR result get the same file-level
    traversal a retrieved commit already gets.
    """
    with driver.session() as session:
        result = session.run(
            """
            MATCH (pr:PullRequest {repo: $repo, number: $number})-[:CONTAINS]->(c:Commit)
            RETURN c.sha AS sha
            """,
            repo=repo_full_name,
            number=int(pr_number),
        )
        return [record["sha"] for record in result]

    

def get_module_graph(driver: Driver, repo_full_name: str) -> dict:
    """
    Groups files into module-level clusters using their top-level
    directory as the module name. This is a stated heuristic, not an
    inferred architectural boundary -- clustering by real import-graph
    community detection is a much harder unsupervised problem, out of
    scope here. Directory structure is a reasonable, explainable
    stand-in when a repo is already organized that way.

    Returns module-level nodes (with file counts) and aggregated
    IMPORTS edges between modules (weight = number of underlying
    file-to-file import edges), computed directly from the existing
    File/IMPORTS graph -- no new data or schema needed.
    """
    with driver.session() as session:
        modules_result = session.run(
            """
            MATCH (f:File {repo: $repo})
            WHERE f.path CONTAINS '/'
            WITH split(f.path, '/')[0] AS module, count(*) AS file_count
            RETURN module, file_count
            ORDER BY file_count DESC
            """,
            repo=repo_full_name,
        )
        modules = [dict(r) for r in modules_result]

        edges_result = session.run(
            """
            MATCH (a:File {repo: $repo})-[:IMPORTS]->(b:File {repo: $repo})
            WITH split(a.path, '/')[0] AS from_module, split(b.path, '/')[0] AS to_module
            WHERE from_module <> to_module
            RETURN from_module, to_module, count(*) AS weight
            ORDER BY weight DESC
            """,
            repo=repo_full_name,
        )
        edges = [dict(r) for r in edges_result]

    return {"modules": modules, "edges": edges}

    

def get_file_count(driver: Driver, repo_full_name: str) -> int:
    """
    Real file count from the graph -- used for the sidebar's repo stats
    instead of a hardcoded number that could drift from reality after
    re-ingestion.
    """
    with driver.session() as session:
        result = session.run(
            "MATCH (f:File {repo: $repo}) RETURN count(f) AS count",
            repo=repo_full_name,
        )
        return result.single()["count"]