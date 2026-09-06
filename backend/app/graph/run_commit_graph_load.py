"""
Fetches per-commit file details for commits new since the last graph
sync, loads Person/Commit/File relationships into Neo4j, and derives
file ownership from edit frequency.

Incremental: tracks last_commit_graph_sync_at on the repo row, so
re-running this only processes commits authored since the last run,
instead of always re-fetching the same bounded batch. On first run
(no sync mark yet), falls back to the most recent COMMIT_LIMIT commits.

Run with:
    docker compose exec api python -m app.graph.run_commit_graph_load
"""

from app.db.session import SessionLocal
from app.models.raw import RawRepository
from app.ingestion.github_client import get_commit_detail
from app.graph.neo4j_client import driver
from app.graph.loader import load_commit_graph, derive_ownership
from app.graph.sync_state import get_new_commits, mark_commit_graph_synced

REPO = "httpie/cli"
COMMIT_LIMIT = 50

session = SessionLocal()
repo = session.query(RawRepository).filter_by(full_name=REPO).first()

commits = get_new_commits(session, repo, limit=COMMIT_LIMIT)
shas = [c.sha for c in commits]

print(f"Fetching file details for {len(shas)} commits new since last graph sync...")
details = []
for sha in shas:
    detail = get_commit_detail("httpie", "cli", sha)
    details.append(detail)

if details:
    print("Loading commit graph into Neo4j...")
    load_commit_graph(driver, REPO, details)

    print("Deriving file ownership...")
    derive_ownership(driver, REPO)
else:
    print("No new commits since last sync -- nothing to load.")

mark_commit_graph_synced(session, repo)
session.close()

print("Done.")