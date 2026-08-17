from neo4j import Driver
from sqlalchemy.orm import Session

from app.retrieval.search import search
from app.graph.queries import get_files_for_commit, get_blast_radius, get_owner


def investigate(
    pg_session: Session,
    neo4j_driver: Driver,
    repo_id: int,
    repo_full_name: str,
    query: str,
    top_k: int = 5,
) -> list[dict]:
    """
    The core deliverable: takes a plain-English query, retrieves the
    most relevant commits/PRs by meaning, then for each one, walks the
    graph to find which real files were touched, their derived owner,
    and their blast radius -- turning a vague description into a
    concrete, explained, traceable answer.

    PRs are a known, stated limitation here: retrieval can surface a
    relevant PR, but since we never linked PRs to the commits inside
    them, PR results don't get file-level traversal -- only commits do.
    That's honest scope, not an oversight papered over.
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
            files = get_files_for_commit(neo4j_driver, repo_full_name, c["source_id"])
            for f in files:
                owner = get_owner(neo4j_driver, repo_full_name, f)
                blast = get_blast_radius(neo4j_driver, repo_full_name, f, max_hops=2)
                entry["files"].append(
                    {
                        "path": f,
                        "owner": owner["owner"] if owner else None,
                        "blast_radius_count": len(blast),
                    }
                )

        results.append(entry)

    return results