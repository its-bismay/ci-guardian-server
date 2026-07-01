import httpx
from ..core.config import settings

TELEGRAM_API = f"https://api.telegram.org/bot{settings.telegram_bot_token}"


async def send_message(chat_id: str, text: str, reply_markup: dict | None = None):
    async with httpx.AsyncClient() as client:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        await client.post(f"{TELEGRAM_API}/sendMessage", json=payload)


async def send_failure_alert(
    chat_id: str,
    repo_name: str,
    branch: str,
    workflow: str,
    summary: str,
    confidence: int,
    category: str,
    report_url: str,
):
    text = (
        f"🔴 Build Failed — {repo_name}\n\n"
        f"Branch: {branch}\n"
        f"Workflow: {workflow}\n\n"
        f"Root cause: {summary}\n\n"
        f"Confidence: {confidence}%\n"
        f"Category: {category}\n\n"
        f"[View Full Report →]({report_url})"
    )
    await send_message(chat_id, text)
