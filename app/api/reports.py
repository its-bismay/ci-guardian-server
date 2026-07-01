from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..core.deps import get_current_user
from ..models import Report, Run, Repo, Installation
from ..schemas import ReportOut, FeedbackIn
from ..db.session import get_session

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{run_id}", response_model=ReportOut | dict)
async def get_report(
    run_id: str,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Report)
        .join(Run)
        .join(Repo)
        .join(Installation)
        .where(Run.id == run_id, Installation.user_id == user.id)
    )
    report = result.scalar_one_or_none()
    if not report:
        return {"error": "no report available"}
    return report


@router.post("/{run_id}/feedback")
async def submit_feedback(
    run_id: str,
    body: FeedbackIn,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Report)
        .join(Run)
        .join(Repo)
        .join(Installation)
        .where(Run.id == run_id, Installation.user_id == user.id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"ok": True, "helpful": body.helpful}


@router.get("/{run_id}/pr-comment")
async def get_pr_comment_status(
    run_id: str,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Report.pr_number, Report.github_comment_id)
        .join(Run)
        .join(Repo)
        .join(Installation)
        .where(Run.id == run_id, Installation.user_id == user.id)
    )
    row = result.one_or_none()
    if not row:
        return {"posted": False}
    return {"posted": row.github_comment_id is not None, "pr_number": row.pr_number, "comment_id": row.github_comment_id}
