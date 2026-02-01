"""
Signals API Routes

Endpoints match the Lovable frontend schema (see lovable_ds.md).
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.chat.handler import handle_chat_message
from app.pipeline.orchestrator import run_pipeline, refresh_company
from app.pipeline.mongodb import (
    list_companies, get_company, search_companies,
    toggle_watchlist, connect_db
)
from app.services.formatter import (
    format_company, format_signals_for_company,
    format_search_results, format_pipeline_output,
    format_company_highlights
)
from app.services.news_monitor import stream_news, news_monitor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

# In-memory job store (use Redis in production)
_jobs: dict[str, dict] = {}


# =============================================================================
# Request/Response Models
# =============================================================================

class ChatRequest(BaseModel):
    message: str


class SearchRequest(BaseModel):
    query: str
    filters: dict | None = None


class AnalyzeRequest(BaseModel):
    name: str | None = None
    url: str | None = None
    document: str | None = None  # base64


class WatchlistRequest(BaseModel):
    slug: str
    enabled: bool = True


class NotifyRequest(BaseModel):
    jobId: str
    email: str


# =============================================================================
# Helpers
# =============================================================================

def _serialize(obj: Any) -> Any:
    """Fix MongoDB ObjectId and datetime serialization."""
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(v) for v in obj]
    if isinstance(obj, ObjectId):
        return str(obj)
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return obj


# =============================================================================
# Health & Status
# =============================================================================

@router.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "Signals Intelligence API"
    }


# =============================================================================
# Search & Jobs (Lovable Schema)
# =============================================================================

@router.post("/search")
async def create_search(req: SearchRequest, background_tasks: BackgroundTasks):
    """
    Initiate a market search.
    Returns a jobId for polling.
    """
    job_id = str(uuid.uuid4())

    # Initialize job
    _jobs[job_id] = {
        "id": job_id,
        "status": "pending",
        "progress": 0,
        "isComplete": False,
        "query": req.query,
        "results": None,
        "error": None,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }

    # Run pipeline in background
    background_tasks.add_task(_run_search_job, job_id, req.query)

    return {"jobId": job_id}


async def _run_search_job(job_id: str, query: str):
    """Background task to run the pipeline."""
    try:
        _jobs[job_id]["status"] = "processing"
        _jobs[job_id]["progress"] = 10

        # Run pipeline
        result = await run_pipeline(name=query)

        _jobs[job_id]["progress"] = 90

        # Format results
        _jobs[job_id]["results"] = _serialize(result)
        _jobs[job_id]["status"] = "completed"
        _jobs[job_id]["progress"] = 100
        _jobs[job_id]["isComplete"] = True

    except Exception as e:
        logger.error(f"Search job {job_id} failed: {e}")
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = str(e)
        _jobs[job_id]["isComplete"] = True


@router.get("/job/{job_id}/status")
async def get_job_status(job_id: str):
    """
    Poll for job progress.
    Returns JobStatus schema.
    """
    job = _jobs.get(job_id)
    if not job:
        return {"error": "Job not found", "status": "failed", "isComplete": True}

    return {
        "id": job["id"],
        "status": job["status"],
        "progress": job["progress"],
        "isComplete": job["isComplete"],
        "error": job.get("error"),
    }


@router.get("/job/{job_id}/results")
async def get_job_results(job_id: str):
    """
    Get final results when job completes.
    Returns SearchResults schema.
    """
    job = _jobs.get(job_id)
    if not job:
        return {"error": "Job not found"}

    if not job["isComplete"]:
        return {"error": "Job not complete", "status": job["status"]}

    if job["status"] == "failed":
        return {"error": job.get("error", "Job failed")}

    # Return formatted results
    result = job.get("results", {})

    # If it's already formatted pipeline output
    if "company" in result:
        company = result["company"]
        return {
            "companies": [company],
            "signals": {company.get("signal", "other"): [company]} if company.get("signal") else {},
            "metadata": {
                "totalMatches": 1,
                "queryTokens": job["query"].split(),
                "searchDurationMs": 0
            }
        }

    return result


# =============================================================================
# Company Endpoints (Lovable Schema)
# =============================================================================

@router.get("/companies")
async def get_companies(watchlist: bool = False):
    """
    List all companies in Lovable schema format.
    """
    raw_companies = list_companies(watchlist_only=watchlist)
    formatted = [format_company(c) for c in raw_companies]
    return {"companies": _serialize(formatted)}


@router.get("/companies/search")
async def search_companies_endpoint(q: str = ""):
    """
    Full-text search on companies.
    """
    raw_companies = search_companies(q)
    formatted = [format_company(c) for c in raw_companies]
    return {"companies": _serialize(formatted)}


@router.get("/company/{slug}")
async def get_single_company(slug: str):
    """
    Get a single company by slug.
    Returns Company schema.
    """
    raw = get_company(slug)
    if not raw:
        return {"error": "Not found"}

    formatted = format_company(raw)
    return _serialize(formatted)


@router.get("/company/{slug}/signals")
async def get_company_signals(slug: str):
    """
    Get all signals for a company.
    Returns Signal[] schema.
    """
    raw = get_company(slug)
    if not raw:
        return {"error": "Not found"}

    company_id = str(raw.get("_id", uuid.uuid4()))
    signals = format_signals_for_company(raw, company_id)
    return _serialize(signals)


@router.get("/company/{slug}/highlights")
async def get_company_highlights(slug: str):
    """
    Get key metric highlights for a company.

    Returns structured data with:
    - hiring: openRoles, status, topDepartments, growth indicator
    - funding: totalRaised, amountNumeric, lastRound, growth indicator
    - signals: positive[], negative[], overall growth, score, sentiment
    """
    raw = get_company(slug)
    if not raw:
        return {"error": "Not found"}

    highlights = format_company_highlights(raw)
    return _serialize(highlights)


@router.get("/highlights")
async def get_all_highlights(watchlist: bool = False, limit: int = 20):
    """
    Get metric highlights for all companies.

    Returns array of company highlights sorted by signal strength.

    Query params:
    - watchlist: Filter to watchlisted companies only
    - limit: Max companies to return (default 20)
    """
    raw_companies = list_companies(watchlist_only=watchlist)

    highlights = []
    for raw in raw_companies[:limit]:
        h = format_company_highlights(raw)
        highlights.append(h)

    # Sort by signal score (highest first), then by positive signals count
    highlights.sort(
        key=lambda x: (
            x["signals"].get("score") or 0,
            len(x["signals"].get("positive", []))
        ),
        reverse=True
    )

    return {
        "highlights": _serialize(highlights),
        "count": len(highlights),
        "metadata": {
            "watchlistOnly": watchlist,
            "limit": limit
        }
    }


# =============================================================================
# Analysis Endpoints
# =============================================================================

@router.post("/analyze")
async def analyze(req: AnalyzeRequest):
    """
    Trigger full pipeline and return formatted results.
    """
    if not any([req.name, req.url, req.document]):
        return {"error": "Provide name, url, or document"}

    try:
        result = await run_pipeline(
            name=req.name,
            url=req.url,
            document_base64=req.document
        )
        return {"success": True, "data": _serialize(result)}
    except Exception as e:
        logger.error(f"[api] Analyze error: {e}")
        return {"error": str(e)}


@router.post("/analyze/{slug}/refresh")
async def refresh(slug: str):
    """
    Re-run pipeline for an existing company.
    """
    try:
        result = await refresh_company(slug)
        if not result:
            return {"error": "Not found"}
        return {"success": True, "data": _serialize(result)}
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# Watchlist
# =============================================================================

@router.post("/watchlist")
async def update_watchlist(req: WatchlistRequest):
    """Toggle watchlist status for a company."""
    toggle_watchlist(req.slug, req.enabled)
    return {"success": True}


# =============================================================================
# Chat (Streaming)
# =============================================================================

@router.post("/chat")
async def chat(req: ChatRequest):
    """Streaming chat via SSE."""
    async def stream():
        async for event in handle_chat_message(req.message):
            yield f"data: {json.dumps(_serialize(event))}\n\n"
    return StreamingResponse(stream(), media_type="text/event-stream")


# =============================================================================
# Notifications (Stub)
# =============================================================================

@router.post("/notify/subscribe")
async def subscribe_notifications(req: NotifyRequest):
    """Subscribe to job completion notifications."""
    # TODO: Implement with Resend
    return {"success": True, "message": f"Will notify {req.email} when job {req.jobId} completes"}


# =============================================================================
# Real-time News Stream
# =============================================================================

@router.get("/news/stream")
async def stream_tech_news():
    """
    Stream real-time tech news as Server-Sent Events.

    Monitors: AI/ML, Developer Tools, Cloud, Cybersecurity, Fintech

    Each event is a JSON object:
    {
        "id": "unique-id",
        "domain": "AI & Machine Learning",
        "headline": "OpenAI announces...",
        "summary": "Full summary text...",
        "source": "Firecrawl Search",
        "timestamp": "2024-01-31T12:00:00Z",
        "relevance": "high" | "medium" | "low"
    }
    """
    return StreamingResponse(
        stream_news(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/news/latest")
async def get_latest_news(limit: int = 10):
    """Get the latest cached news items (non-streaming)."""
    items = news_monitor.latest_news[-limit:]
    return {"news": [item.to_dict() for item in items]}


@router.post("/news/start")
async def start_news_monitor():
    """Manually start the news monitor if not running."""
    await news_monitor.start()
    return {"success": True, "message": "News monitor started"}


@router.post("/news/stop")
async def stop_news_monitor():
    """Stop the news monitor."""
    await news_monitor.stop()
    return {"success": True, "message": "News monitor stopped"}
