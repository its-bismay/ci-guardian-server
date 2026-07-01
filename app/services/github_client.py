import jwt
import time
import httpx
from datetime import datetime, timezone
from ..core.config import settings


async def get_installation_token(installation_id: int) -> str:
    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + 600,
        "iss": settings.github_app_id,
    }
    app_jwt = jwt.encode(payload, settings.github_app_private_key, algorithm="RS256")

    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github.v3+json",
            },
        )
        data = res.json()
        return data["token"]


async def github_request(method: str, path: str, token: str, **kwargs):
    async with httpx.AsyncClient() as client:
        res = await client.request(
            method,
            f"https://api.github.com{path}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json",
            },
            **kwargs,
        )
        return res


async def get_installation_repos(installation_id: int) -> list[dict]:
    token = await get_installation_token(installation_id)
    res = await github_request("GET", "/installation/repositories", token)
    data = res.json()
    return data.get("repositories", [])


async def fetch_run_metadata(owner: str, repo: str, run_id: int, token: str) -> dict:
    res = await github_request("GET", f"/repos/{owner}/{repo}/actions/runs/{run_id}", token)
    return res.json()


async def fetch_job_logs(owner: str, repo: str, run_id: int, token: str) -> list[dict]:
    jobs_res = await github_request(
        "GET", f"/repos/{owner}/{repo}/actions/runs/{run_id}/jobs", token
    )
    jobs = jobs_res.json().get("jobs", [])
    failed_logs = []

    for job in jobs:
        if job.get("conclusion") == "failure":
            log_res = await github_request(
                "GET", f"/repos/{owner}/{repo}/actions/jobs/{job['id']}/logs", token
            )
            log_text = log_res.text
            failed_logs.append({
                "job_name": job.get("name", ""),
                "logs": log_text,
            })

    return failed_logs


async def fetch_file_content(owner: str, repo: str, path: str, token: str) -> str | None:
    res = await github_request(
        "GET", f"/repos/{owner}/{repo}/contents/{path}", token
    )
    if res.status_code != 200:
        return None
    data = res.json()
    import base64
    return base64.b64decode(data["content"]).decode("utf-8", errors="replace")


async def post_pr_comment(owner: str, repo: str, pr_number: int, body: str, token: str):
    res = await github_request(
        "POST",
        f"/repos/{owner}/{repo}/issues/{pr_number}/comments",
        token,
        json={"body": body},
    )
    return res.json()


async def update_pr_comment(owner: str, repo: str, comment_id: int, body: str, token: str):
    res = await github_request(
        "PATCH",
        f"/repos/{owner}/{repo}/issues/comments/{comment_id}",
        token,
        json={"body": body},
    )
    return res.json()
