"""
Runs the full ingestion pipeline against the real demo repo and prints
a summary. Safe to run more than once.

Run with:
    docker compose exec api python -m app.ingestion.run_ingestion
"""

from app.db.session import SessionLocal
from app.ingestion.pipeline import ingest_repo

session = SessionLocal()
try:
    repo = ingest_repo(session, "httpie", "cli", max_pages=2)
    print(f"Ingested repo: {repo.full_name}")
    print(f"  Description: {repo.description}")
    print(f"  Commits stored: {len(repo.commits)}")
    print(f"  PRs stored: {len(repo.pull_requests)}")
finally:
    session.close()