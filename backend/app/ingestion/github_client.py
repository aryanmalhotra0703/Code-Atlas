import requests

from app.core.config import settings

GITHUB_API_BASE = "https://api.github.com"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github+json",
    }


def get_repo(owner: str, repo: str) -> dict:
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
    response = requests.get(url, headers=_headers(), timeout=10)
    response.raise_for_status()
    return response.json()


def _paginated_get(url: str, params: dict, max_pages: int) -> list[dict]:
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


def get_commits(owner: str, repo: str, max_pages: int = 5, since: str | None = None) -> list[dict]:
    """
    since, when provided, is an ISO 8601 timestamp -- GitHub's own commits
    endpoint supports filtering to only commits authored after this date,
    which is what makes re-running ingestion cheap after the first time.
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits"
    params = {"per_page": 100}
    if since:
        params["since"] = since
    return _paginated_get(url, params=params, max_pages=max_pages)


def get_pull_requests(owner: str, repo: str, max_pages: int = 5) -> list[dict]:
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls"
    params = {"per_page": 100, "state": "all"}
    return _paginated_get(url, params=params, max_pages=max_pages)


def get_commit_detail(owner: str, repo: str, sha: str) -> dict:
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits/{sha}"
    response = requests.get(url, headers=_headers(), timeout=15)
    response.raise_for_status()
    return response.json()