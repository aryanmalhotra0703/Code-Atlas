"""
Runs the full Milestone 2 pipeline end-to-end: downloads real repo
source, parses and resolves imports, and loads the result into Neo4j
as an actual graph.

Run with:
    docker compose exec api python -m app.graph.run_graph_load
"""

from app.ingestion.repo_source import download_repo_source
from app.ingestion.parser.import_resolver import build_import_edges
from app.graph.neo4j_client import driver
from app.graph.loader import load_file_graph, count_graph

OWNER = "httpie"
REPO_NAME = "cli"
REPO = f"{OWNER}/{REPO_NAME}"  # derived from the same values used to download,
                                # never a separate constant that could drift
                                # out of sync with what was actually fetched

files = download_repo_source(OWNER, REPO_NAME)
print(f"Downloaded {len(files)} Python files")

edges = build_import_edges(files)
print(f"Resolved {len(edges)} internal import edges")

load_file_graph(driver, REPO, edges)
print("Loaded into Neo4j")

counts = count_graph(driver, REPO)
print(f"Neo4j now contains: {counts['files']} File nodes, {counts['edges']} IMPORTS edges")