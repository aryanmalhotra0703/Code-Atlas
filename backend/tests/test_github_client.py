import pytest
import requests

from app.ingestion.github_client import get_repo, RepoNotFoundError


class _FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error")

    def json(self):
        return {}


def test_get_repo_raises_clear_error_on_404(monkeypatch):
    """
    Mocks requests.get so this test never hits the real network -- fast,
    reliable, and doesn't depend on GitHub's actual API behavior or a
    valid token being present.
    """
    def fake_get(*args, **kwargs):
        return _FakeResponse(404)

    monkeypatch.setattr(requests, "get", fake_get)

    with pytest.raises(RepoNotFoundError):
        get_repo("nonexistent-owner", "nonexistent-repo")