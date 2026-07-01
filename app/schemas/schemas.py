from pydantic import BaseModel
from typing import Any
from datetime import datetime


class UserOut(BaseModel):
    id: str
    github_id: int
    github_username: str
    avatar_url: str
    email: str

    model_config = {"from_attributes": True}


class RepoOut(BaseModel):
    id: str
    full_name: str
    is_monitored: bool
    added_at: datetime | None = None

    model_config = {"from_attributes": True}


class RunOut(BaseModel):
    id: str
    repo_id: str
    repo_full_name: str | None = None
    github_run_id: int
    workflow_name: str
    branch: str
    commit_sha: str
    status: str
    conclusion: str
    duration_seconds: int | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    has_report: bool = False
    summary: str | None = None

    model_config = {"from_attributes": True}


class ReportOut(BaseModel):
    id: str
    run_id: str
    category: str
    summary: str
    root_cause: str
    evidence: list[Any]
    proposed_fix: str
    confidence: int
    is_flaky_guess: bool
    model_used: str
    pr_number: int | None = None
    github_comment_id: int | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class FeedbackIn(BaseModel):
    helpful: bool


class ToggleRepoIn(BaseModel):
    is_monitored: bool


class NotificationChannelOut(BaseModel):
    id: str
    channel_type: str
    external_id: str
    verified: bool

    model_config = {"from_attributes": True}


class NotificationPreferenceOut(BaseModel):
    id: str
    repo_id: str | None = None
    repo_name: str | None = None
    notify_on_failure: bool
    notify_on_success: bool
    post_pr_comment: bool
    channels: list[str]

    model_config = {"from_attributes": True}


class NotificationPreferenceIn(BaseModel):
    notify_on_failure: bool | None = None
    notify_on_success: bool | None = None
    post_pr_comment: bool | None = None
    channels: list[str] | None = None


class AnalysisResult(BaseModel):
    summary: str
    root_cause: str
    evidence: list[str]
    proposed_fix: str
    confidence: int
    is_flaky_guess: bool
    category: str
