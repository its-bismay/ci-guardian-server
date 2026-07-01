from fastapi import APIRouter, HTTPException, status, Request, Header
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy import select
from ..core.config import settings
from ..core.security import create_jwt, decode_jwt
from ..db.session import get_session
from ..models import User
import httpx

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/github/login")
async def github_login():
    params = f"client_id={settings.github_client_id}&scope=user:email&redirect_uri={settings.app_url}/auth/github/callback"
    return RedirectResponse(f"https://github.com/login/oauth/authorize?{params}")


@router.get("/github/callback")
async def github_callback(code: str):
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": f"{settings.app_url}/auth/github/callback",
            },
            headers={"Accept": "application/json"},
        )
        token_data = token_res.json()
        access_token = token_data.get("access_token")
        if not access_token:
            detail = token_data.get("error_description", token_data.get("error", "GitHub OAuth failed"))
            raise HTTPException(status_code=400, detail=detail)

        user_res = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        )
        gh_user = user_res.json()

    async for session in get_session():
        result = await session.execute(select(User).where(User.github_id == gh_user["id"]))
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                github_id=gh_user["id"],
                github_username=gh_user["login"],
                avatar_url=gh_user.get("avatar_url", ""),
                email=gh_user.get("email", ""),
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        jwt_token = create_jwt({"user_id": user.id})
        return RedirectResponse(url=f"{settings.frontend_url}/auth/callback?token={jwt_token}")


@router.post("/logout")
async def logout():
    return JSONResponse({"ok": True})


@router.get("/me")
async def get_me(request: Request, authorization: str = Header(None)):
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_jwt(token)
    async for session in get_session():
        user = await session.get(User, payload["user_id"])
        if not user:
            raise HTTPException(status_code=401)
        return {
            "id": user.id,
            "github_id": user.github_id,
            "github_username": user.github_username,
            "avatar_url": user.avatar_url,
            "email": user.email,
        }
