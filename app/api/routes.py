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
from app.pipeline.openrouter import calculate_vector_scores

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


@router.get("/companies/{slug}/vector-scores")
async def get_vector_scores(slug: str):
    """
    Calculate cross-vector scores for a company using AI analysis.
    Returns scores (0-100) for: hiring_velocity, product_signals,
    external_attention, funding_activity, and market_momentum.
    """
    company = get_company(slug)
    if not company:
        return {"error": "Company not found"}

    try:
        scores = await calculate_vector_scores(
            name=company.get("name", slug),
            company_data=company
        )
        return {"success": True, "scores": _s(scores)}
    except Exception as e:
        logger.error(f"[api] Vector scores error for {slug}: {e}")
        return {"error": str(e)}


@router.post("/watchlist")
async def update_watchlist(req: WatchlistRequest):
    toggle_watchlist(req.slug, req.enabled)
    return {"success": True}