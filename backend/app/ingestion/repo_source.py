import io
import tarfile

import requests

GITHUB_API_BASE = "https://api.github.com"


def download_repo_source(owner: str, repo: str, ref: str = "HEAD") -> dict[str, str]:
    """
    Downloads the repo's source as a tarball and returns every .py file's
    path mapped to its raw source code, held in memory.

    Using GitHub's tarball endpoint instead of `git clone` avoids needing
    a git binary inside the container at all, and instead of fetching
    files one-by-one through the API (hundreds of requests for a repo
    this size), it's a single download, fully extracted in memory.
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/tarball/{ref}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    files: dict[str, str] = {}
    with tarfile.open(fileobj=io.BytesIO(response.content), mode="r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile() or not member.name.endswith(".py"):
                continue
            extracted = tar.extractfile(member)
            if extracted is None:
                continue

            relative_path = member.name.split("/", 1)[1] if "/" in member.name else member.name

            try:
                files[relative_path] = extracted.read().decode("utf-8")
            except UnicodeDecodeError:
                continue

    return files