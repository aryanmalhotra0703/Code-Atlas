"""
Runs the full end-to-end investigation: query -> retrieval -> graph
traversal -> a ranked, explained answer. This is the actual core
deliverable of the whole project.

Run with:
    docker compose exec api python -m app.investigate.check_investigate
"""

from app.db.session import SessionLocal
from app.models.raw import RawRepository
from app.graph.neo4j_client import driver
from app.investigate.engine import investigate

REPO = "httpie/cli"
QUERY = "SSL certificate verification is failing"

pg_session = SessionLocal()
repo = pg_session.query(RawRepository).filter_by(full_name=REPO).first()

results = investigate(pg_session, driver, repo.id, REPO, QUERY, top_k=5)
pg_session.close()

print(f"Query: {QUERY}\n")
for r in results:
    print(f"[{r['type']}] {r['id']}  (similarity: {r['similarity']})")
    print(f"  {r['preview']}")
    for f in r["files"]:
        print(f"    -> {f['path']}  (owner: {f['owner']}, blast radius: {f['blast_radius_count']} files)")
    print()