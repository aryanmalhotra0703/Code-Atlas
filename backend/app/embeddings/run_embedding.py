"""
Embeds all commit messages and PRs for httpie/cli that haven't been
embedded yet, storing them in Postgres via pgvector.

Run with:
    docker compose exec api python -m app.embeddings.run_embedding
"""

from app.db.session import SessionLocal
from app.models.raw import RawRepository
from app.embeddings.pipeline import embed_repo

REPO = "httpie/cli"

session = SessionLocal()
repo = session.query(RawRepository).filter_by(full_name=REPO).first()
stored = embed_repo(session, repo.id)
session.close()

print(f"Stored {stored} new embeddings for {REPO}")