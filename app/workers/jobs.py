import asyncio
from ..services.analysis.pipeline import run_analysis, persist_and_notify


async def run_analysis_pipeline(run_id: str, installation_id: int):
    try:
        result = await run_analysis(run_id)
        await persist_and_notify(run_id, result)
    except Exception as e:
        import traceback
        print(f"Analysis pipeline failed for run {run_id}: {e}")
        traceback.print_exc()
