"""
Fetches per-commit file details for a bounded set of commits already
stored in Postgres, loads Person/Commit/File relationships into Neo4j,
and derives file ownership from commit frequency.

Run with:
    docker compose exec api python -m app.graph.run_commit_graph_load
"""

from app.db.session import SessionLocal
from app.models.raw import RawCommit, RawRepository
from app.ingestion.github_client import get_commit_detail
from app.graph.neo4j_client import driver
from app.graph.loader import load_commit_graph, derive_ownership

REPO = "httpie/cli"
COMMIT_LIMIT = 50

session = SessionLocal()
repo = session.query(RawRepository).filter_by(full_name=REPO).first()
commits = session.query(RawCommit).filter_by(repo_id=repo.id).limit(COMMIT_LIMIT).all()
shas = [c.sha for c in commits]
session.close()

print(f"Fetching file details for {len(shas)} commits...")
details = []
for sha in shas:
    detail = get_commit_detail("httpie", "cli", sha)
    details.append(detail)

print("Loading commit graph into Neo4j...")
load_commit_graph(driver, REPO, details)

print("Deriving file ownership...")
derive_ownership(driver, REPO)

print("Done.")