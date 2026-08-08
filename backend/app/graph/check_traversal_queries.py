"""
Runs the traversal queries against the real graph built earlier in
Milestone 2, using a file we already know is well-connected.

Run with:
    docker compose exec api python -m app.graph.check_traversal_queries
"""

from app.graph.neo4j_client import driver
from app.graph.queries import get_blast_radius, get_recent_changes_near, get_owner

REPO = "httpie/cli"
FILE = "httpie/core.py"

print(f"Blast radius for {FILE}:")
for path in get_blast_radius(driver, REPO, FILE):
    print(f"  {path}")

print(f"\nRecent changes near {FILE}:")
for change in get_recent_changes_near(driver, REPO, FILE):
    print(f"  [{change['file']}] {change['message']}  (by {change['author']})")

print(f"\nOwner of {FILE}:")
owner = get_owner(driver, REPO, FILE)
print(f"  {owner}")