"""
Downloads real httpie source and runs the AST import parser against it,
so we can see genuine results before wiring this into the graph.

Run with:
    docker compose exec api python -m app.ingestion.parser.check_import_parser
"""

from app.ingestion.repo_source import download_repo_source
from app.ingestion.parser.python_imports import extract_imports

files = download_repo_source("httpie", "cli")
print(f"Downloaded {len(files)} Python files")

shown = 0
for path, source in files.items():
    try:
        imports = extract_imports(source)
    except SyntaxError:
        continue  # a handful of real-world files may not parse cleanly

    if imports and shown < 5:
        print(f"\n{path}")
        for imp in imports:
            print(f"  imports: {imp}")
        shown += 1