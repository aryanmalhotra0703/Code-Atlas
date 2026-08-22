from neo4j import Driver
from sqlalchemy.orm import Session

from app.retrieval.search import search
from app.graph.queries import (
    get_files_for_commit,
    get_commits_for_pr,
    get_blast_radius,
    get_owner,
)
from app.graph.loader import load_pr_commit_links, load_commit_graph
from app.ingestion.github_client import get_pr_commits, get_commit_detail


def _files_for_commit_with_fallback(
    neo4j_driver: Driver, repo_full_name: str, sha: str
) -> list[str]:
    """
    Checks the graph first. If a commit has no MODIFIES edges yet, it
    means run_commit_graph_load's bounded batch never covered it -- so
    we fetch and load its file details right now, on the spot. A real
    commit always touches at least one file, so an empty result here
    reliably means "not loaded yet," not "genuinely touches nothing."
    """
    files = get_files_for_commit(neo4j_driver, repo_full_name, sha)
    if not files:
        owner, repo = repo_full_name.split("/", 1)
        detail = get_commit_detail(owner, repo, sha)
        load_commit_graph(neo4j_driver, repo_full_name, [detail])
        files = get_files_for_commit(neo4j_driver, repo_full_name, sha)
    return files


def _commits_for_pr_with_fallback(
    neo4j_driver: Driver, repo_full_name: str, pr_number: str
) -> list[str]:
    """
    Checks Neo4j first for already-linked commits. If none exist, fetches
    and links them from GitHub right now -- lazy loading instead of
    relying on a fixed bulk limit having happened to cover this PR.
    """
    shas = get_commits_for_pr(neo4j_driver, repo_full_name, pr_number)
    if not shas:
        owner, repo = repo_full_name.split("/", 1)
        commits = get_pr_commits(owner, repo, int(pr_number))
        shas = [c["sha"] for c in commits]
        if shas:
            load_pr_commit_links(neo4j_driver, repo_full_name, int(pr_number), shas)
    return shas


def _traverse_files(neo4j_driver: Driver, repo_full_name: str, file_paths: list[str]) -> list[dict]:
    files = []
    for f in file_paths:
        owner = get_owner(neo4j_driver, repo_full_name, f)
        blast = get_blast_radius(neo4j_driver, repo_full_name, f, max_hops=2)
        files.append(
            {
                "path": f,
                "owner": owner["owner"] if owner else None,
                "blast_radius_count": len(blast),
                "blast_radius_files": blast,
            }
        )
    return files


def investigate(
    pg_session: Session,
    neo4j_driver: Driver,
    repo_id: int,
    repo_full_name: str,
    query: str,
    top_k: int = 5,
) -> list[dict]:
    """
    Takes a plain-English query, retrieves the most relevant commits/PRs
    by meaning, then walks the graph to find real files touched, their
    derived owner, and their blast radius -- fetching any missing detail
    (PR<->commit links, commit<->file details) lazily on the spot rather
    than depending on a fixed bulk-load limit having covered it.
    """
    candidates = search(pg_session, repo_id, query, top_k=top_k)

    results = []
    for c in candidates:
        entry = {
            "type": c["source_type"],
            "id": c["source_id"],
            "similarity": round(c["similarity"], 3),
            "preview": c["content"].splitlines()[0][:100] if c["content"] else "",
            "files": [],
        }

        if c["source_type"] == "commit":
            file_paths = _files_for_commit_with_fallback(neo4j_driver, repo_full_name, c["source_id"])
            entry["files"] = _traverse_files(neo4j_driver, repo_full_name, file_paths)

        elif c["source_type"] == "pull_request":
            shas = _commits_for_pr_with_fallback(neo4j_driver, repo_full_name, c["source_id"])
            file_paths: set[str] = set()
            for sha in shas:
                file_paths.update(_files_for_commit_with_fallback(neo4j_driver, repo_full_name, sha))
            entry["files"] = _traverse_files(neo4j_driver, repo_full_name, sorted(file_paths))

        results.append(entry)

    return results