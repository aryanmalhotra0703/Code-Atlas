import requests

from app.core.config import settings

GITHUB_API_BASE = "https://api.github.com"


def _headers() -> dict:
    """
    Every request needs the same auth header, so it lives in one place.
    The 'Accept' header pins us to GitHub's stable REST API version —
    without it GitHub still works, but you're implicitly trusting whatever
    their default response shape happens to be today.
    """
    return {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github+json",
    }


def get_repo(owner: str, repo: str) -> dict:
    """
    Fetches top-level repo metadata: description, language, star count, etc.
    This is a single object, no pagination needed.
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
    response = requests.get(url, headers=_headers(), timeout=10)
    response.raise_for_status()
    return response.json()


def _paginated_get(url: str, params: dict, max_pages: int) -> list[dict]:
    """
    Shared pagination logic for any GitHub list endpoint (commits, PRs,
    issues, etc. all paginate the same way). GitHub returns up to 100
    items per page, newest-first, and signals a next page via the
    response's 'Link' header rather than a field in the JSON body itself —
    requests parses that header into response.links automatically.
    """
    items = []
    while url and len(items) // 100 < max_pages:
        response = requests.get(url, headers=_headers(), params=params, timeout=10)
        response.raise_for_status()
        page = response.json()
        if not page:
            break
        items.extend(page)

        next_link = response.links.get("next")
        url = next_link["url"] if next_link else None
        params = {}

    return items


def get_commits(owner: str, repo: str, max_pages: int = 5) -> list[dict]:
    """
    max_pages caps this at 500 commits by default. That's a deliberate
    scope decision: httpie has thousands of commits total, but the newest
    few hundred already give retrieval and traversal plenty of real signal
    to work with, without a slow first ingestion run while developing.
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits"
    return _paginated_get(url, params={"per_page": 100}, max_pages=max_pages)


def get_pull_requests(owner: str, repo: str, max_pages: int = 5) -> list[dict]:
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls"
    params = {"per_page": 100, "state": "all"}  # 'all' includes closed/merged, not just open
    return _paginated_get(url, params=params, max_pages=max_pages)


def get_commit_detail(owner: str, repo: str, sha: str) -> dict:
    """
    Fetches full detail for a single commit, including the list of files
    it touched. This is a separate endpoint from get_commits() -- the
    bulk list endpoint used for Milestone 1 ingestion is cheap and
    paginated, but doesn't include per-commit file changes. Getting that
    detail requires one request per commit, which is why callers bound
    how many commits they fetch this way rather than doing it for all of
    them.
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits/{sha}"
    response = requests.get(url, headers=_headers(), timeout=15)
    response.raise_for_status()
    return response.json()