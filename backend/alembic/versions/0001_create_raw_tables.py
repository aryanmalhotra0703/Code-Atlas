"""create raw ingestion tables

Revision ID: 0001
Revises:
Create Date: 2026-08-06

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "raw_repositories",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("github_id", sa.BigInteger, nullable=False, unique=True),
        sa.Column("full_name", sa.String, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("primary_language", sa.String, nullable=True),
        sa.Column("stars", sa.Integer, nullable=False, server_default="0"),
        sa.Column("default_branch", sa.String, nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "raw_commits",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("repo_id", sa.Integer, sa.ForeignKey("raw_repositories.id"), nullable=False),
        sa.Column("sha", sa.String, nullable=False, unique=True),
        sa.Column("message", sa.Text, nullable=True),
        sa.Column("author_name", sa.String, nullable=True),
        sa.Column("author_email", sa.String, nullable=True),
        sa.Column("authored_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "raw_pull_requests",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("repo_id", sa.Integer, sa.ForeignKey("raw_repositories.id"), nullable=False),
        sa.Column("number", sa.Integer, nullable=False),
        sa.Column("title", sa.Text, nullable=True),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("author", sa.String, nullable=True),
        sa.Column("state", sa.String, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("merged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("repo_id", "number", name="uq_pr_repo_number"),
    )


def downgrade() -> None:
    op.drop_table("raw_pull_requests")
    op.drop_table("raw_commits")
    op.drop_table("raw_repositories")