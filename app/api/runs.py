from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from ..core.deps import get_current_user
from ..models import Run, Repo, Report, Installation
from ..schemas import RunOut
from ..db.session import get_session

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("")
async def list_runs(
    repo_id: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    query = (
        select(Run, Repo.full_name, Report.summary)
        .join(Repo)
        .join(Installation)
        .where(Installation.user_id == user.id)
        .outerjoin(Report)
        .order_by(desc(Run.created_at))
    )

    if repo_id:
        query = query.where(Repo.id == repo_id)
    if status:
        query = query.where(Run.status == status)

    offset = (page - 1) * 50
    query = query.offset(offset).limit(50)
    result = await session.execute(query)
    rows = result.all()

    runs_out = []
    for run, full_name, summary in rows:
        runs_out.append(RunOut(
            id=run.id,
            repo_id=run.repo_id,
            repo_full_name=full_name,
            github_run_id=run.github_run_id,
            workflow_name=run.workflow_name,
            branch=run.branch,
            commit_sha=run.commit_sha,
            status=run.status,
            conclusion=run.conclusion,
            duration_seconds=run.duration_seconds,
            started_at=run.started_at,
            finished_at=run.finished_at,
            has_report=summary is not None,
            summary=summary,
        ))

    return {"runs": runs_out, "page": page}


@router.get("/{run_id}")
async def get_run(
    run_id: str,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Run, Repo.full_name)
        .join(Repo)
        .join(Installation)
        .where(Run.id == run_id, Installation.user_id == user.id)
    )
    row = result.one_or_none()
    if not row:
        return {"error": "not found"}, 404
    run, full_name = row
    return RunOut(
        id=run.id,
        repo_id=run.repo_id,
        repo_full_name=full_name,
        github_run_id=run.github_run_id,
        workflow_name=run.workflow_name,
        branch=run.branch,
        commit_sha=run.commit_sha,
        status=run.status,
        conclusion=run.conclusion,
        duration_seconds=run.duration_seconds,
        started_at=run.started_at,
        finished_at=run.finished_at,
    ).model_dump()
