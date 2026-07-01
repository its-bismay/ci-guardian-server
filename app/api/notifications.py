import secrets
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..core.config import settings
from ..core.deps import get_current_user
from ..models import User, NotificationChannel, NotificationPreference, Repo, Installation
from ..schemas import NotificationChannelOut, NotificationPreferenceOut, NotificationPreferenceIn
from ..db.session import get_session

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/channels", response_model=list[NotificationChannelOut])
async def list_channels(
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(NotificationChannel).where(NotificationChannel.user_id == user.id)
    )
    return result.scalars().all()


@router.post("/telegram/link-code")
async def generate_telegram_link(
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    code = secrets.token_hex(8)
    bot_username = "ci_guardian_bot"
    url = f"https://t.me/{bot_username}?start={code}"
    return {"url": url, "code": code}


@router.get("/preferences", response_model=list[NotificationPreferenceOut])
async def list_preferences(
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(NotificationPreference)
        .where(NotificationPreference.user_id == user.id)
    )
    prefs = result.scalars().all()

    out = []
    for p in prefs:
        repo_name = None
        if p.repo_id:
            repo = await session.get(Repo, p.repo_id)
            repo_name = repo.full_name if repo else None
        out.append(NotificationPreferenceOut(
            id=p.id,
            repo_id=p.repo_id,
            repo_name=repo_name,
            notify_on_failure=p.notify_on_failure,
            notify_on_success=p.notify_on_success,
            post_pr_comment=p.post_pr_comment,
            channels=list(p.channels) if p.channels else [],
        ))
    return out


@router.patch("/preferences")
async def update_preferences(
    body: NotificationPreferenceIn,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == user.id)
    )
    prefs = result.scalars().first()
    if not prefs:
        prefs = NotificationPreference(user_id=user.id)
        session.add(prefs)
    if body.notify_on_failure is not None:
        prefs.notify_on_failure = body.notify_on_failure
    if body.notify_on_success is not None:
        prefs.notify_on_success = body.notify_on_success
    if body.post_pr_comment is not None:
        prefs.post_pr_comment = body.post_pr_comment
    if body.channels is not None:
        prefs.channels = body.channels
    await session.commit()
    return {"ok": True}
