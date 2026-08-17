"""
Runs a real natural-language query against the embedded httpie data,
to prove retrieval actually finds relevant commits/PRs by meaning.

Run with:
    docker compose exec api python -m app.retrieval.check_search
"""

from app.db.session import SessionLocal
from app.models.raw import RawRepository
from app.retrieval.search import search

REPO = "httpie/cli"
QUERY = "SSL certificate verification is failing"

session = SessionLocal()
repo = session.query(RawRepository).filter_by(full_name=REPO).first()

results = search(session, repo.id, QUERY, top_k=5)
session.close()

print(f"Query: {QUERY}\n")
for r in results:
    preview = r["content"].splitlines()[0][:80]
    print(f"[{r['source_type']}] {r['source_id']}  (similarity: {r['similarity']:.3f})")
    print(f"  {preview}\n")