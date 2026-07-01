import secrets
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from ..core.config import settings
from ..core.deps import get_current_user
from ..models import User, NotificationChannel, NotificationPreference, Repo, Installation, BackgroundJob
from ..schemas import NotificationChannelOut, NotificationPreferenceOut, NotificationPreferenceIn
from ..db.session import get_session
import httpx

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
    job = BackgroundJob(
        job_type="telegram_link",
        status="pending",
        payload={"code": code, "user_id": user.id},
    )
    session.add(job)
    await session.commit()

    bot_username = settings.telegram_bot_username or "ci_guardian_bot"
    url = f"https://t.me/{bot_username}?start={code}"
    return {"url": url, "code": code, "job_id": job.id}


@router.get("/telegram/status")
async def telegram_status(
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    channel = await session.execute(
        select(NotificationChannel).where(
            NotificationChannel.user_id == user.id,
            NotificationChannel.channel_type == "telegram",
            NotificationChannel.verified == True,
        )
    )
    return {"connected": channel.scalar_one_or_none() is not None}


@router.post("/telegram/webhook")
async def telegram_webhook(request: Request, session: AsyncSession = Depends(get_session)):
    body = await request.json()
    message = body.get("message", {})
    text = (message.get("text") or "").strip()
    chat_id = str(message.get("chat", {}).get("id", ""))

    if not text.startswith("/start "):
        return {"ok": True}

    code = text.split(" ", 1)[1].strip()
    if not code or not chat_id:
        return {"ok": True}

    result = await session.execute(
        select(BackgroundJob).where(
            BackgroundJob.job_type == "telegram_link",
            BackgroundJob.status == "pending",
        ).order_by(desc(BackgroundJob.created_at))
    )
    job = next((j for j in result.scalars().all() if j.payload.get("code") == code), None)
    if not job:
        return {"ok": True}

    user_id = job.payload.get("user_id")
    existing = await session.execute(
        select(NotificationChannel).where(
            NotificationChannel.user_id == user_id,
            NotificationChannel.channel_type == "telegram",
        )
    )
    channel = existing.scalar_one_or_none()
    if channel:
        channel.external_id = chat_id
        channel.verified = True
    else:
        session.add(NotificationChannel(
            user_id=user_id,
            channel_type="telegram",
            external_id=chat_id,
            verified=True,
        ))

    job.status = "completed"
    job.result = {"chat_id": chat_id}
    await session.commit()

    from ..services.telegram_client import send_message
    await send_message(chat_id, "✅ CI Guardian connected! You'll receive failure alerts here.")

    return {"ok": True}


@router.post("/telegram/setup-webhook")
async def setup_telegram_webhook():
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=400, detail="TELEGRAM_BOT_TOKEN not configured")
    url = f"{settings.app_url}/notifications/telegram/webhook"
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/setWebhook",
            params={"url": url},
        )
        data = res.json()
        if not data.get("ok"):
            raise HTTPException(status_code=400, detail=data.get("description", "Failed to set webhook"))
        return {"ok": True, "description": data.get("description")}


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
