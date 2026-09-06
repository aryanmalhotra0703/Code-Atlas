from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.raw import RawRepository, RawCommit, RawPullRequest


def get_new_commits(session: Session, repo: RawRepository, limit: int = 50) -> list[RawCommit]:
    """
    Returns commits authored after the last graph sync, newest first,
    capped at `limit`. On a repo's first graph sync (last_commit_graph_sync_at
    is None), this returns the most recent `limit` commits overall --
    same bounded-first-pass behavior as before, just now tracked so a
    second run doesn't redundantly re-fetch commits already processed.
    """
    query = session.query(RawCommit).filter(RawCommit.repo_id == repo.id)
    if repo.last_commit_graph_sync_at is not None:
        query = query.filter(RawCommit.authored_date > repo.last_commit_graph_sync_at)
    return query.order_by(RawCommit.authored_date.desc()).limit(limit).all()


def get_new_prs(session: Session, repo: RawRepository, limit: int = 50) -> list[RawPullRequest]:
    """Same idea as get_new_commits, for PRs."""
    query = session.query(RawPullRequest).filter(RawPullRequest.repo_id == repo.id)
    if repo.last_pr_graph_sync_at is not None:
        query = query.filter(RawPullRequest.created_at > repo.last_pr_graph_sync_at)
    return query.order_by(RawPullRequest.created_at.desc()).limit(limit).all()


def mark_commit_graph_synced(session: Session, repo: RawRepository) -> None:
    repo.last_commit_graph_sync_at = datetime.now(timezone.utc)
    session.commit()


def mark_pr_graph_synced(session: Session, repo: RawRepository) -> None:
    repo.last_pr_graph_sync_at = datetime.now(timezone.utc)
    session.commit()