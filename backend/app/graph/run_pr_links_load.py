"""
Fetches which commits belong to PRs new since the last graph sync, and
loads PullRequest -> Commit CONTAINS edges into Neo4j.

Incremental: tracks last_pr_graph_sync_at, so re-running only processes
PRs created since the last run instead of always reprocessing the same
bounded batch.

Run with:
    docker compose exec api python -m app.graph.run_pr_links_load
"""

from app.db.session import SessionLocal
from app.models.raw import RawRepository
from app.ingestion.github_client import get_pr_commits
from app.graph.neo4j_client import driver
from app.graph.loader import load_pr_commit_links
from app.graph.sync_state import get_new_prs, mark_pr_graph_synced

REPO = "httpie/cli"
PR_LIMIT = 50

session = SessionLocal()
repo = session.query(RawRepository).filter_by(full_name=REPO).first()

prs = get_new_prs(session, repo, limit=PR_LIMIT)
numbers = [pr.number for pr in prs]

print(f"Fetching commit links for {len(numbers)} PRs new since last graph sync...")
linked = 0
for number in numbers:
    commits = get_pr_commits("httpie", "cli", number)
    shas = [c["sha"] for c in commits]
    if shas:
        load_pr_commit_links(driver, REPO, number, shas)
        linked += 1

mark_pr_graph_synced(session, repo)
session.close()

print(f"Linked {linked} PRs to their commits in Neo4j")