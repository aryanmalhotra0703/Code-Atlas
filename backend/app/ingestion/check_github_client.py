"""
Quick manual check that github_client.py actually works against a real repo.
Not a pytest test (those come later, mocked) — this hits the real GitHub API
on purpose, so you can see genuine data and catch integration problems early.

Run with:
    docker compose exec api python -m app.ingestion.check_github_client
"""

from app.ingestion.github_client import get_repo, get_commits, get_pull_requests

OWNER, REPO = "httpie", "cli"

repo = get_repo(OWNER, REPO)
print(f"Repo: {repo['full_name']}")
print(f"  Description: {repo['description']}")
print(f"  Language: {repo['language']}")
print(f"  Stars: {repo['stargazers_count']}")

commits = get_commits(OWNER, REPO, max_pages=2)
print(f"\nFetched {len(commits)} commits")
print(f"  Most recent: {commits[0]['commit']['message'].splitlines()[0]}")
print(f"  By: {commits[0]['commit']['author']['name']}")

prs = get_pull_requests(OWNER, REPO, max_pages=2)
print(f"\nFetched {len(prs)} pull requests")
print(f"  Most recent: #{prs[0]['number']} {prs[0]['title']}")
print(f"  State: {prs[0]['state']}")