import json
import logging
from typing import Any

from bson import ObjectId
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.chat.handler import handle_chat_message
from app.pipeline.orchestrator import run_pipeline, refresh_company
from app.pipeline.mongodb import list_companies, get_company, search_companies, toggle_watchlist
from app.pipeline.hn_search import search_hn, search_hn_with_context
from app.pipeline.hn_reporter import generate_and_send_report

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

# Models
class ChatRequest(BaseModel):
    message: str

class AnalyzeRequest(BaseModel):
    name: str | None = None
    url: str | None = None
    document: str | None = None  # base64

class WatchlistRequest(BaseModel):
    slug: str
    enabled: bool = True

class HNReportRequest(BaseModel):
    company_name: str
    email: str
    keywords: list[str] | None = None
    include_comments: bool = True
    limit: int = 5

# Helper to fix MongoDB ObjectId serialization
def _s(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _s(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_s(v) for v in obj]
    if isinstance(obj, ObjectId):
        return str(obj)
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return obj

# Endpoints
@router.post("/chat")
async def chat(req: ChatRequest):
    """Streaming chat via SSE."""
    async def stream():
        async for event in handle_chat_message(req.message):
            yield f"data: {json.dumps(_s(event))}\n\n"
    return StreamingResponse(stream(), media_type="text/event-stream")

@router.post("/analyze")
async def analyze(req: AnalyzeRequest):
    """Trigger full pipeline manually."""
    if not any([req.name, req.url, req.document]):
        return {"error": "Provide name, url, or document"}
    try:
        profile = await run_pipeline(
            name=req.name, url=req.url, document_base64=req.document
        )
        return {"success": True, "company": _s(profile)}
    except Exception as e:
        logger.error(f"[api] Analyze error: {e}")
        return {"error": str(e)}

@router.post("/analyze/{slug}/refresh")
async def refresh(slug: str):
    try:
        profile = await refresh_company(slug)
        if not profile: return {"error": "Not found"}
        return {"success": True, "company": _s(profile)}
    except Exception as e:
        return {"error": str(e)}

@router.get("/companies")
async def get_companies(watchlist: bool = False):
    return {"companies": _s(list_companies(watchlist_only=watchlist))}

@router.get("/companies/search")
async def search(q: str = ""):
    return {"companies": _s(search_companies(q))}

@router.get("/companies/{slug}")
async def get_single_company(slug: str):
    c = get_company(slug)
    return {"company": _s(c)} if c else {"error": "Not found"}

@router.post("/watchlist")
async def update_watchlist(req: WatchlistRequest):
    toggle_watchlist(req.slug, req.enabled)
    return {"success": True}

@router.post("/reports/hn")
async def generate_hn_report(req: HNReportRequest):
    """
    Generate an HN intelligence report and send via email.

    Searches Hacker News for discussions about the company,
    analyzes sentiment and themes, and sends a formatted report.
    """
    try:
        # Build search queries from company name and optional keywords
        queries = [req.company_name]
        if req.keywords:
            queries.extend(req.keywords)

        # Search HN for each query (with or without comments)
        all_discussions = []
        for query in queries:
            if req.include_comments:
                results = await search_hn_with_context(query, limit=req.limit)
            else:
                results = await search_hn(query, limit=req.limit)
            all_discussions.extend(results)

        # Deduplicate by objectID
        seen_ids = set()
        unique_discussions = []
        for d in all_discussions:
            if d["objectID"] not in seen_ids:
                seen_ids.add(d["objectID"])
                unique_discussions.append(d)

        # Sort by points (most popular first) and limit
        unique_discussions.sort(key=lambda x: x.get("points", 0), reverse=True)
        unique_discussions = unique_discussions[:req.limit]

        # Generate analysis and send email
        result = await generate_and_send_report(
            company_name=req.company_name,
            discussions=unique_discussions,
            to_email=req.email,
        )

        return {
            "success": True,
            "verdict": result.get("verdict"),
            "discussions_found": len(unique_discussions),
            "email_sent": result.get("email_sent"),
            "analysis": _s(result.get("analysis")),
        }

    except Exception as e:
        logger.error(f"[api] HN report error: {e}")
        return {"success": False, "error": str(e)}

@router.get("/reports/hn/search")
async def search_hn_only(q: str, limit: int = 5):
    """Search HN without generating a report (for preview)."""
    try:
        discussions = await search_hn(q, limit=limit)
        return {"success": True, "discussions": _s(discussions)}
    except Exception as e:
        return {"success": False, "error": str(e)}