from datetime import datetime

from sqlalchemy import ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class RawRepository(Base):
    __tablename__ = "raw_repositories"

    id: Mapped[int] = mapped_column(primary_key=True)
    github_id: Mapped[int] = mapped_column(unique=True)
    full_name: Mapped[str]
    description: Mapped[str | None]
    primary_language: Mapped[str | None]
    stars: Mapped[int] = mapped_column(default=0)
    default_branch: Mapped[str | None]
    ingested_at: Mapped[datetime] = mapped_column(server_default=func.now())
    last_synced_at: Mapped[datetime | None]

    commits: Mapped[list["RawCommit"]] = relationship(back_populates="repo")
    pull_requests: Mapped[list["RawPullRequest"]] = relationship(back_populates="repo")


class RawCommit(Base):
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