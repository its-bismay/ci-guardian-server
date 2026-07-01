from urllib.parse import urlparse, urlencode, parse_qs
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from ..core.config import settings


def clean_async_url(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    query.pop("sslmode", None)
    query.pop("channel_binding", None)
    clean_query = urlencode(query, doseq=True)
    if clean_query:
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{clean_query}"
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


database_url = clean_async_url(settings.database_url)
engine = create_async_engine(database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
