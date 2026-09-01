"""
Stress test: runs the graph-loading pipeline against a genuinely large
real repo (django/django, thousands of Python files) instead of the
much smaller httpie/cli (133 files) used throughout development. The
goal is finding where this actually slows down at scale, not just
confirming it works on a small, friendly demo repo.

Run with:
    docker compose exec api python -m app.graph.stress_test_django
"""

import time

from app.ingestion.repo_source import download_repo_source
from app.ingestion.parser.import_resolver import build_import_edges
from app.graph.neo4j_client import driver
from app.graph.loader import load_file_graph, count_graph

OWNER = "django"
REPO_NAME = "django"
REPO = f"{OWNER}/{REPO_NAME}"

t0 = time.perf_counter()
files = download_repo_source(OWNER, REPO_NAME)
t1 = time.perf_counter()
print(f"Downloaded {len(files)} Python files in {t1 - t0:.1f}s")

edges = build_import_edges(files)
t2 = time.perf_counter()
print(f"Resolved {len(edges)} internal import edges in {t2 - t1:.1f}s")

load_file_graph(driver, REPO, edges)
t3 = time.perf_counter()
print(f"Loaded into Neo4j in {t3 - t2:.1f}s")

counts = count_graph(driver, REPO)
print(f"Neo4j now contains: {counts['files']} File nodes, {counts['edges']} IMPORTS edges")
print(f"Total time: {t3 - t0:.1f}s")