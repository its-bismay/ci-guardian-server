"""initial schema

Revision ID: 001
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("github_id", sa.BigInteger(), unique=True, nullable=False),
        sa.Column("github_username", sa.String(), nullable=False),
        sa.Column("avatar_url", sa.String(), default=""),
        sa.Column("email", sa.String(), default=""),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_table(
        "installations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("github_installation_id", sa.BigInteger(), unique=True, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_table(
        "repos",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("installation_id", sa.String(), sa.ForeignKey("installations.id"), nullable=False),
        sa.Column("github_repo_id", sa.BigInteger(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("is_monitored", sa.Boolean(), default=True),
        sa.Column("notify_on_success", sa.Boolean(), default=False),
        sa.Column("added_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_table(
        "runs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("repo_id", sa.String(), sa.ForeignKey("repos.id"), nullable=False),
        sa.Column("github_run_id", sa.BigInteger(), nullable=False),
        sa.Column("workflow_name", sa.String(), default=""),
        sa.Column("branch", sa.String(), default=""),
        sa.Column("commit_sha", sa.String(), default=""),
        sa.Column("commit_message", sa.String(), default=""),
        sa.Column("triggered_by", sa.String(), default=""),
        sa.Column("status", sa.String(), default="queued"),
        sa.Column("conclusion", sa.String(), default=""),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("finished_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_table(
        "reports",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("run_id", sa.String(), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("category", sa.String(), default=""),
        sa.Column("summary", sa.String(), default=""),
        sa.Column("root_cause", sa.Text(), default=""),
        sa.Column("evidence", sa.JSON(), default=list),
        sa.Column("proposed_fix", sa.Text(), default=""),
        sa.Column("confidence", sa.Integer(), default=0),
        sa.Column("is_flaky_guess", sa.Boolean(), default=False),
        sa.Column("raw_log_ref", sa.String(), default=""),
        sa.Column("model_used", sa.String(), default=""),
        sa.Column("pr_number", sa.Integer(), nullable=True),
        sa.Column("github_comment_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_table(
        "notification_channels",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("channel_type", sa.String(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("verified", sa.Boolean(), default=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("repo_id", sa.String(), sa.ForeignKey("repos.id"), nullable=True),
        sa.Column("notify_on_failure", sa.Boolean(), default=True),
        sa.Column("notify_on_success", sa.Boolean(), default=False),
        sa.Column("post_pr_comment", sa.Boolean(), default=True),
        sa.Column("channels", sa.JSON(), default=list),
    )
    op.create_table(
        "background_jobs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("job_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), default="pending"),
        sa.Column("payload", sa.JSON(), default=dict),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_table("background_jobs")
    op.drop_table("notification_preferences")
    op.drop_table("notification_channels")
    op.drop_table("reports")
    op.drop_table("runs")
    op.drop_table("repos")
    op.drop_table("installations")
    op.drop_table("users")
