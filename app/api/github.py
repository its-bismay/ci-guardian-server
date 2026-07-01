from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..core.config import settings
from ..core.deps import get_current_user
from ..models import User, Installation, Repo
from ..schemas import RepoOut, ToggleRepoIn
from ..db.session import get_session
from ..services.github_client import get_installation_repos, get_installation_token

router = APIRouter(prefix="/github", tags=["github"])


@router.get("/install-url")
async def get_install_url():
    url = f"https://github.com/apps/{settings.github_app_name}/installations/new"
    return {"url": url}


@router.get("/installation/callback")
async def installation_callback(
    installation_id: int,
    setup_action: str = "install",
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    existing = await session.execute(
        select(Installation).where(Installation.github_installation_id == installation_id)
    )
    if not existing.scalar_one_or_none():
        inst = Installation(
            user_id=user.id,
            github_installation_id=installation_id,
        )
        session.add(inst)
        await session.commit()

        repos = await get_installation_repos(installation_id)
        for r in repos:
            repo_exists = await session.execute(
                select(Repo).where(Repo.github_repo_id == r["id"])
            )
            if not repo_exists.scalar_one_or_none():
                session.add(Repo(
                    installation_id=inst.id,
                    github_repo_id=r["id"],
                    full_name=r["full_name"],
                ))
        await session.commit()

    return {"ok": True, "installation_id": installation_id}


@router.get("/repos", response_model=list[RepoOut])
async def list_repos(
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Repo)
        .join(Installation)
        .where(Installation.user_id == user.id)
        .order_by(Repo.full_name)
    )
    return result.scalars().all()


@router.post("/repos/{repo_id}/toggle")
async def toggle_repo(
    repo_id: str,
    body: ToggleRepoIn,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Repo)
        .join(Installation)
        .where(Repo.id == repo_id, Installation.user_id == user.id)
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repo not found")
    repo.is_monitored = body.is_monitored
    await session.commit()
    return {"ok": True}
