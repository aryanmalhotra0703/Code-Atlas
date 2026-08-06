from datetime import datetime

from sqlalchemy import ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class RawRepository(Base):
    """
    One row per ingested repo. github_id (not full_name) is the unique
    identity, because full_name can change if a repo is renamed or
    transferred — github_id never does. This is exactly the kind of thing
    that only becomes obvious once you hit it: httpie/httpie actually
    redirects to httpie/cli under the hood.
    """
    __tablename__ = "raw_repositories"

    id: Mapped[int] = mapped_column(primary_key=True)
    github_id: Mapped[int] = mapped_column(unique=True)
    full_name: Mapped[str]
    description: Mapped[str | None]
    primary_language: Mapped[str | None]
    stars: Mapped[int] = mapped_column(default=0)
    default_branch: Mapped[str | None]
    ingested_at: Mapped[datetime] = mapped_column(server_default=func.now())

    commits: Mapped[list["RawCommit"]] = relationship(back_populates="repo")
    pull_requests: Mapped[list["RawPullRequest"]] = relationship(back_populates="repo")


class RawCommit(Base):
    """
    sha is globally unique (it's a git hash), so it's the natural unique
    key here — this is what lets ingestion be re-run safely without
    creating duplicate rows for commits already stored.
    """
    __tablename__ = "raw_commits"

    id: Mapped[int] = mapped_column(primary_key=True)
    repo_id: Mapped[int] = mapped_column(ForeignKey("raw_repositories.id"))
    sha: Mapped[str] = mapped_column(unique=True)
    message: Mapped[str | None]
    author_name: Mapped[str | None]
    author_email: Mapped[str | None]
    authored_date: Mapped[datetime | None]
    ingested_at: Mapped[datetime] = mapped_column(server_default=func.now())

    repo: Mapped["RawRepository"] = relationship(back_populates="commits")


class RawPullRequest(Base):
    """
    PR numbers are only unique *within* a repo (repo A's PR #5 and repo B's
    PR #5 are unrelated), so the real unique key is the pair (repo_id, number) —
    that's what UniqueConstraint below enforces.
    """
    __tablename__ = "raw_pull_requests"
    __table_args__ = (UniqueConstraint("repo_id", "number", name="uq_pr_repo_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    repo_id: Mapped[int] = mapped_column(ForeignKey("raw_repositories.id"))
    number: Mapped[int]
    title: Mapped[str | None]
    body: Mapped[str | None]
    author: Mapped[str | None]
    state: Mapped[str | None]
    created_at: Mapped[datetime | None]
    merged_at: Mapped[datetime | None]
    ingested_at: Mapped[datetime] = mapped_column(server_default=func.now())

    repo: Mapped["RawRepository"] = relationship(back_populates="pull_requests")