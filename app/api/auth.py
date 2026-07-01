from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import RedirectResponse, JSONResponse
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config as StarletteConfig
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.config import settings
from ..core.security import create_jwt, decode_jwt
from ..core.deps import get_optional_user
from ..db.session import get_session
from ..models import User
from fastapi import Depends
import httpx

router = APIRouter(prefix="/auth", tags=["auth"])

starlette_config = StarletteConfig(environ={
    "GITHUB_CLIENT_ID": settings.github_client_id,
    "GITHUB_CLIENT_SECRET": settings.github_client_secret,
})
oauth = OAuth(starlette_config)
oauth.register(
    name="github",
    authorize_url="https://github.com/login/oauth/authorize",
    authorize_params={"scope": "user:email"},
    access_token_url="https://github.com/login/oauth/access_token",
    access_token_params=None,
    client_kwargs={"scope": "user:email"},
)


@router.get("/github/login")
async def github_login():
    params = f"client_id={settings.github_client_id}&scope=user:email&redirect_uri={settings.app_url}/auth/github/callback"
    return RedirectResponse(f"https://github.com/login/oauth/authorize?{params}")


@router.get("/github/callback")
async def github_callback(code: str, request: Request):
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
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
        response = RedirectResponse(url=f"{settings.frontend_url}/dashboard")
        response.set_cookie(
            key="session",
            value=jwt_token,
            httponly=True,
            secure=settings.environment == "production",
            samesite="lax",
            max_age=settings.jwt_expire_minutes * 60,
        )
        return response


@router.post("/logout")
async def logout():
    response = JSONResponse({"ok": True})
    response.delete_cookie("session", path="/")
    return response


@router.get("/me")
async def get_me(request: Request):
    user_data = await get_optional_user(request)
    if not user_data:
        raise HTTPException(status_code=401, detail="Not authenticated")
    async for session in get_session():
        user = await session.get(User, user_data["user_id"])
        if not user:
            raise HTTPException(status_code=401)
        return {
            "id": user.id,
            "github_id": user.github_id,
            "github_username": user.github_username,
            "avatar_url": user.avatar_url,
            "email": user.email,
        }
