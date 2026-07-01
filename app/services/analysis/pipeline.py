import json
import re
import httpx
from ...core.config import settings
from ...models import Report, Run, Repo, Installation
from ...schemas import AnalysisResult
from ...db.session import async_session
from ..github_client import (
    fetch_run_metadata,
    fetch_job_logs,
    fetch_file_content,
    get_installation_token,
    post_pr_comment,
    update_pr_comment,
)
from ..telegram_client import send_failure_alert
from ...api.events import push_event
from .prompts import TRIAGE_SYSTEM_PROMPT, TRIAGE_HUMAN_PROMPT


def truncate_logs(logs: list[dict], max_lines: int = 300) -> str:
    output = []
    for job in logs:
        lines = job["logs"].split("\n")
        error_lines = [l for l in lines if any(p in l.upper() for p in ["ERROR", "FAILED", "TRACEBACK", "##[ERROR]", "EXCEPTION"])]
        last_lines = lines[-max_lines:]
        deduplicated = list(dict.fromkeys(last_lines))
        combined = error_lines + deduplicated
        combined = combined[:max_lines]
        output.append(f"=== {job['job_name']} ===\n" + "\n".join(combined))
    return "\n\n".join(output)


def extract_stack_trace_files(log_text: str) -> list[str]:
    files = re.findall(r'(?:File\s+)"?([^"\n]+\.(?:py|js|ts|tsx|jsx|java|go|rs))"?', log_text)
    files += re.findall(r'(?:at\s+|in\s+)([^\s:]+\.(?:py|js|ts|tsx|jsx|java|go|rs))(?::\d+)', log_text)
    return list(set(files))


async def openrouter_complete(messages: list[dict]) -> str:
    async with httpx.AsyncClient(timeout=120) as client:
        res = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": settings.app_url,
            },
            json={
                "model": settings.openrouter_model,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 4000,
                "response_format": {"type": "json_object"},
            },
        )
        data = res.json()
        return data["choices"][0]["message"]["content"]


async def run_analysis(run_id: str) -> AnalysisResult:
    async with async_session() as session:
        run = await session.get(Run, run_id)
        repo = await session.get(Repo, run.repo_id)
        installation = await session.get(Installation, repo.installation_id)

        owner, repo_name = repo.full_name.split("/")
        token = await get_installation_token(installation.github_installation_id)

        metadata = await fetch_run_metadata(owner, repo_name, run.github_run_id, token)
        raw_logs = await fetch_job_logs(owner, repo_name, run.github_run_id, token)

        truncated = truncate_logs(raw_logs)

        stack_files = extract_stack_trace_files(truncated)
        repo_context_parts = []
        for f in stack_files[:5]:
            content = await fetch_file_content(owner, repo_name, f, token)
            if content:
                lines = content.split("\n")
                trimmed = "\n".join(lines[:100])
                repo_context_parts.append(f"=== {f} ===\n{trimmed}")

        repo_context = "\n\n".join(repo_context_parts) if repo_context_parts else "No relevant source files found in stack traces."

        messages = [
            {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
            {"role": "user", "content": TRIAGE_HUMAN_PROMPT.format(
                logs=truncated[:6000],
                repo_context=repo_context[:4000],
                workflow_name=metadata.get("name", ""),
                branch=run.branch,
                job_name=raw_logs[0]["job_name"] if raw_logs else "unknown",
            )},
        ]

        response = await openrouter_complete(messages)
        result = json.loads(response)
        return AnalysisResult(**result)


async def persist_and_notify(run_id: str, result: AnalysisResult):
    url = f"{settings.app_url}/runs/{run_id}"
    async with async_session() as session:
        from sqlalchemy import select

        run = await session.get(Run, run_id)
        repo = await session.get(Repo, run.repo_id)
        installation = await session.get(Installation, repo.installation_id)

        existing_result = await session.execute(
            select(Report).where(Report.run_id == run_id)
        )
        existing = existing_result.scalar_one_or_none()

        if existing:
            for field in ["category", "summary", "root_cause", "evidence", "proposed_fix", "confidence", "is_flaky_guess"]:
                setattr(existing, field, getattr(result, field))
            existing.model_used = settings.openrouter_model
            report = existing
        else:
            report = Report(
                run_id=run_id,
                category=result.category,
                summary=result.summary,
                root_cause=result.root_cause,
                evidence=result.evidence,
                proposed_fix=result.proposed_fix,
                confidence=result.confidence,
                is_flaky_guess=result.is_flaky_guess,
                model_used=settings.openrouter_model,
            )
            session.add(report)

        await session.commit()
        await session.refresh(report)

        owner, repo_name = repo.full_name.split("/")
        token = await get_installation_token(installation.github_installation_id)

        pr_number = run.triggered_by
        if pr_number and pr_number.isdigit():
            report.pr_number = int(pr_number)
            comment_body = (
                f"### 🔴 CI Guardian: Build Failed\n\n"
                f"**Root cause:** {result.summary}\n\n"
                f"**Confidence:** {result.confidence}% · **Category:** {result.category}\n\n"
                f"**Proposed fix:**\n```diff\n{result.proposed_fix}\n```\n\n"
                f"<sub>Powered by CI Guardian · [View full report]({url})</sub>"
            )

            if report.github_comment_id:
                await update_pr_comment(owner, repo_name, report.github_comment_id, comment_body, token)
            else:
                comment = await post_pr_comment(owner, repo_name, report.pr_number, comment_body, token)
                report.github_comment_id = comment["id"]

        await session.commit()

        push_event(installation.user_id, {
            "id": run.id,
            "repo_full_name": repo.full_name,
            "workflow_name": run.workflow_name,
            "branch": run.branch,
            "conclusion": run.conclusion,
            "summary": result.summary,
            "has_report": True,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "duration_seconds": run.duration_seconds,
        })

        from ...models import NotificationChannel
        channels_result = await session.execute(
            select(NotificationChannel).where(
                NotificationChannel.user_id == installation.user_id,
                NotificationChannel.verified == True,
            )
        )
        for ch in channels_result.scalars().all():
            if ch.channel_type == "telegram":
                await send_failure_alert(
                    chat_id=ch.external_id,
                    repo_name=repo.full_name,
                    branch=run.branch,
                    workflow=run.workflow_name,
                    summary=result.summary,
                    confidence=result.confidence,
                    category=result.category,
                    report_url=url,
                )

        return report
