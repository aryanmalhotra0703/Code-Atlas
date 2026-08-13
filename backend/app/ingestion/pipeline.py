from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.ingestion.github_client import get_repo, get_commits, get_pull_requests
from app.models.raw import RawRepository, RawCommit, RawPullRequest


def ingest_repo(session: Session, owner: str, name: str, max_pages: int = 5) -> RawRepository:
    existing = session.query(RawRepository).filter_by(full_name=f"{owner}/{name}").first()
    since = existing.last_synced_at.isoformat() if existing and existing.last_synced_at else None

    repo_data = get_repo(owner, name)

    repo_stmt = (
        pg_insert(RawRepository)
        .values(
            github_id=repo_data["id"],
            full_name=repo_data["full_name"],
            description=repo_data.get("description"),
            primary_language=repo_data.get("language"),
            stars=repo_data.get("stargazers_count", 0),
            default_branch=repo_data.get("default_branch"),
            last_synced_at=datetime.now(timezone.utc),
        )
        .on_conflict_do_update(
            index_elements=["github_id"],
            set_={
                "description": repo_data.get("description"),
                "primary_language": repo_data.get("language"),
                "stars": repo_data.get("stargazers_count", 0),
                "last_synced_at": datetime.now(timezone.utc),
            },
        )
        .returning(RawRepository.id)
    )
    repo_id = session.execute(repo_stmt).scalar_one()
    session.commit()

    commits = get_commits(owner, name, max_pages=max_pages, since=since)
    for c in commits:
        author = c["commit"].get("author") or {}
        commit_stmt = (
            pg_insert(RawCommit)
            .values(
                repo_id=repo_id,
                sha=c["sha"],
                message=c["commit"]["message"],
                author_name=author.get("name"),
                author_email=author.get("email"),
                authored_date=author.get("date"),
            )
            .on_conflict_do_nothing(index_elements=["sha"])
        )
        session.execute(commit_stmt)
    session.commit()

    prs = get_pull_requests(owner, name, max_pages=max_pages)
    for pr in prs:
        user = pr.get("user") or {}
        pr_stmt = (
            pg_insert(RawPullRequest)
            .values(
                repo_id=repo_id,
                number=pr["number"],
                title=pr["title"],
                body=pr.get("body"),
                author=user.get("login"),
                state=pr["state"],
                created_at=pr.get("created_at"),
                merged_at=pr.get("merged_at"),
            )
            .on_conflict_do_nothing(index_elements=["repo_id", "number"])
        )
        session.execute(pr_stmt)
    session.commit()

    return session.get(RawRepository, repo_id)