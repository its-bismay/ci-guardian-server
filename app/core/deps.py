from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyCookie
from sqlalchemy.ext.asyncio import AsyncSession
from .security import decode_jwt, get_token_from_cookie
from .config import settings
from ..db.session import get_session

cookie_scheme = APIKeyCookie(name="session")


async def get_optional_user(request):
    token = get_token_from_cookie(request)
    if not token:
        return None
    try:
        return decode_jwt(token)
    except:
        return None


async def get_current_user(request, session: AsyncSession = Depends(get_session)):
    token = get_token_from_cookie(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    payload = decode_jwt(token)
    from ..models import User
    user = await session.get(User, payload["user_id"])
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user
