"""
Fetches which commits belong to each of a bounded set of PRs, and loads
PullRequest -> Commit CONTAINS edges into Neo4j.

Run with:
    docker compose exec api python -m app.graph.run_pr_links_load
"""

from app.db.session import SessionLocal
from app.models.raw import RawPullRequest, RawRepository
from app.ingestion.github_client import get_pr_commits
from app.graph.neo4j_client import driver
from app.graph.loader import load_pr_commit_links

REPO = "httpie/cli"
PR_LIMIT = 50

session = SessionLocal()
repo = session.query(RawRepository).filter_by(full_name=REPO).first()
prs = (
    session.query(RawPullRequest)
    .filter_by(repo_id=repo.id)
    .order_by(RawPullRequest.created_at.desc())
    .limit(PR_LIMIT)
    .all()
)
numbers = [pr.number for pr in prs]
session.close()

print(f"Fetching commit links for {len(numbers)} PRs...")
linked = 0
for number in numbers:
    commits = get_pr_commits("httpie", "cli", number)
    shas = [c["sha"] for c in commits]
    if shas:
        load_pr_commit_links(driver, REPO, number, shas)
        linked += 1

print(f"Linked {linked} PRs to their commits in Neo4j")