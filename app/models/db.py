import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, Integer, BigInteger, Text, Float, ForeignKey, JSON, TIMESTAMP
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def utcnow():
    return datetime.now(timezone.utc)


def new_id():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=new_id)
    github_id = Column(BigInteger, unique=True, nullable=False)
    github_username = Column(String, nullable=False)
    avatar_url = Column(String, default="")
    email = Column(String, default="")
    created_at = Column(TIMESTAMP(timezone=True), default=utcnow)

    installations = relationship("Installation", back_populates="user")


class Installation(Base):
    __tablename__ = "installations"

    id = Column(String, primary_key=True, default=new_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    github_installation_id = Column(BigInteger, unique=True, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=utcnow)

    user = relationship("User", back_populates="installations")
    repos = relationship("Repo", back_populates="installation")


class Repo(Base):
    __tablename__ = "repos"

    id = Column(String, primary_key=True, default=new_id)
    installation_id = Column(String, ForeignKey("installations.id"), nullable=False)
    github_repo_id = Column(BigInteger, nullable=False)
    full_name = Column(String, nullable=False)
    is_monitored = Column(Boolean, default=True)
    notify_on_success = Column(Boolean, default=False)
    added_at = Column(TIMESTAMP(timezone=True), default=utcnow)

    installation = relationship("Installation", back_populates="repos")
    runs = relationship("Run", back_populates="repo")


class Run(Base):
    __tablename__ = "runs"

    id = Column(String, primary_key=True, default=new_id)
    repo_id = Column(String, ForeignKey("repos.id"), nullable=False)
    github_run_id = Column(BigInteger, nullable=False)
    workflow_name = Column(String, default="")
    branch = Column(String, default="")
    commit_sha = Column(String, default="")
    commit_message = Column(String, default="")
    triggered_by = Column(String, default="")
    status = Column(String, default="queued")
    conclusion = Column(String, default="")
    started_at = Column(TIMESTAMP(timezone=True), nullable=True)
    finished_at = Column(TIMESTAMP(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=utcnow)

    repo = relationship("Repo", back_populates="runs")
    report = relationship("Report", back_populates="run", uselist=False)


class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=new_id)
    run_id = Column(String, ForeignKey("runs.id"), nullable=False)
    category = Column(String, default="")
    summary = Column(String, default="")
    root_cause = Column(Text, default="")
    evidence = Column(JSON, default=list)
    proposed_fix = Column(Text, default="")
    confidence = Column(Integer, default=0)
    is_flaky_guess = Column(Boolean, default=False)
    raw_log_ref = Column(String, default="")
    model_used = Column(String, default="")
    pr_number = Column(Integer, nullable=True)
    github_comment_id = Column(BigInteger, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=utcnow)

    run = relationship("Run", back_populates="report")


class NotificationChannel(Base):
    __tablename__ = "notification_channels"

    id = Column(String, primary_key=True, default=new_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    channel_type = Column(String, nullable=False)
    external_id = Column(String, nullable=False)
    verified = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), default=utcnow)


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id = Column(String, primary_key=True, default=new_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    repo_id = Column(String, ForeignKey("repos.id"), nullable=True)
    notify_on_failure = Column(Boolean, default=True)
    notify_on_success = Column(Boolean, default=False)
    post_pr_comment = Column(Boolean, default=True)
    channels = Column(JSON, default=list)


class BackgroundJob(Base):
    __tablename__ = "background_jobs"

    id = Column(String, primary_key=True, default=new_id)
    job_type = Column(String, nullable=False)
    status = Column(String, default="pending")
    payload = Column(JSON, default=dict)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=utcnow, onupdate=utcnow)
