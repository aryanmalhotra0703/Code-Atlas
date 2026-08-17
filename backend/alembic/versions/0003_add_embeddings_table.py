"""add embeddings table with pgvector

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-06

"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

EMBEDDING_DIM = 384


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "embeddings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("repo_id", sa.Integer, sa.ForeignKey("raw_repositories.id"), nullable=False),
        sa.Column("source_type", sa.String, nullable=False),
        sa.Column("source_id", sa.String, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("repo_id", "source_type", "source_id", name="uq_embedding_source"),
    )


def downgrade() -> None:
    op.drop_table("embeddings")