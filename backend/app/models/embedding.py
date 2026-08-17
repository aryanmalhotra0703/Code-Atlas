from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

EMBEDDING_DIM = 384  # all-MiniLM-L6-v2's output size (local model)


class Embedding(Base):
    """
    One row per embedded piece of text -- a commit message or a PR's
    title+body. source_type + source_id together identify exactly which
    original row this embedding represents, so retrieval can trace a
    match back to the real commit/PR it came from.
    """
    __tablename__ = "embeddings"
    __table_args__ = (
        UniqueConstraint("repo_id", "source_type", "source_id", name="uq_embedding_source"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    repo_id: Mapped[int] = mapped_column(ForeignKey("raw_repositories.id"))
    source_type: Mapped[str]  # "commit" or "pull_request"
    source_id: Mapped[str]    # sha for commits, str(number) for PRs
    content: Mapped[str]      # the actual text that was embedded, kept for reference
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())