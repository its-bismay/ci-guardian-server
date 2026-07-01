from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import select
from ..core.security import verify_webhook_signature
from ..db.session import get_session
from ..models import Run, Repo, Installation
from ..workers.jobs import run_analysis_pipeline
from ..services.github_client import fetch_run_metadata
import json

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/github")
async def github_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("x-hub-signature-256", "")
    if not verify_webhook_signature(body, sig):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = request.headers.get("x-github-event", "")
    payload = json.loads(body)

    if event == "workflow_run" and payload.get("action") in ("completed",):
        workflow_run = payload["workflow_run"]
        repo_data = payload["repository"]
        installation_id = payload["installation"]["id"]

        async for session in get_session():
            result = await session.execute(
                select(Installation).where(
                    Installation.github_installation_id == installation_id
                )
            )
            installation = result.scalar_one_or_none()
            if not installation:
                return {"ok": True}

            repo_result = await session.execute(
                select(Repo).where(
                    Repo.github_repo_id == repo_data["id"],
                    Repo.installation_id == installation.id,
                )
            )
            repo = repo_result.scalar_one_or_none()
            if not repo or not repo.is_monitored:
                return {"ok": True}

            prs = workflow_run.get("pull_requests", [])
            triggered_by = str(prs[0]["number"]) if prs else ""

            run = Run(
                repo_id=repo.id,
                github_run_id=workflow_run["id"],
                workflow_name=workflow_run.get("name", ""),
                branch=workflow_run.get("head_branch", ""),
                commit_sha=workflow_run.get("head_sha", ""),
                triggered_by=triggered_by,
                status=workflow_run.get("status", "completed"),
                conclusion=workflow_run.get("conclusion", ""),
            )
            session.add(run)
            await session.commit()
            await session.refresh(run)

            if workflow_run.get("conclusion") == "failure":
                await run_analysis_pipeline(run.id, installation.github_installation_id)

        return {"ok": True}

    return {"ok": True}
