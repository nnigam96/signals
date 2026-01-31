import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

from app.pipeline.firecrawl import crawl_company
from app.pipeline.reducto import parse_document
from app.pipeline.openrouter import analyze_company
from app.pipeline.mongodb import store_company, get_company, store_snapshot, make_slug

logger = logging.getLogger(__name__)

async def run_pipeline(
    name: str | None = None,
    url: str | None = None,
    document_base64: str | None = None,
    document_url: str | None = None,
) -> dict[str, Any]:
    """
    Main pipeline: Crawl (Web) + Parse (Doc) -> Analyze (LLM) -> Store (DB).
    Runs ingestion steps in PARALLEL.
    """
    start = time.time()
    identifier = name or url or "document"
    logger.info(f"[pipeline] Starting for: {identifier}")

    # ── Step 1: Parallel Ingestion (Web + Docs) ──
    # We launch both tasks simultaneously to save time
    tasks = []

    # Task A: Web Crawl
    if url or name:
        logger.info("[pipeline] Queuing web crawl...")
        tasks.append(asyncio.create_task(crawl_company(url or name)))
    else:
        # No web target? Just return empty result
        tasks.append(asyncio.create_task(asyncio.sleep(0, result={"raw": ""})))

    # Task B: Document Parse
    if document_base64 or document_url:
        logger.info("[pipeline] Queuing doc parse...")
        tasks.append(asyncio.create_task(parse_document(document_base64 or document_url)))
    else:
        tasks.append(asyncio.create_task(asyncio.sleep(0, result=None)))

    # Wait for both
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Unpack results with error handling
    web_data = results[0]
    if isinstance(web_data, Exception):
        logger.error(f"[pipeline] Web crawl failed: {web_data}")
        web_data = {"error": str(web_data), "raw": ""}
    
    document_data = results[1]
    if isinstance(document_data, Exception):
        logger.error(f"[pipeline] Doc parse failed: {document_data}")
        document_data = None

    # ── Step 2: AI Analysis ──
    logger.info("[pipeline] Starting AI analysis...")
    analysis = await analyze_company(
        name=name, url=url, web_data=web_data, document_data=document_data
    )
    logger.info("[pipeline] ✓ Analysis complete")

    # ── Step 3: Persistence ──
    company_name = analysis.get("name") or name or "Unknown Company"
    slug = make_slug(company_name)
    now = datetime.now(timezone.utc)

    profile = {
        "name": company_name,
        "slug": slug,
        "description": analysis.get("summary", ""),
        "website": url or analysis.get("website", ""),
        "crawled_at": now,
        "web_data": web_data,
        "document_data": document_data,
        "analysis": analysis,
        "watchlist": False,
        "updated_at": now,
    }

    logger.info("[pipeline] Storing in MongoDB...")
    stored = store_company(profile)
    store_snapshot(slug, {"web_data": web_data, "document_data": document_data, "analysis": analysis})

    elapsed = round(time.time() - start, 1)
    logger.info(f'[pipeline] ✅ Done: "{company_name}" in {elapsed}s')
    return stored

async def refresh_company(slug: str) -> dict[str, Any] | None:
    """Re-run pipeline for an existing company."""
    existing = get_company(slug)
    if not existing:
        return None
    logger.info(f'[pipeline] Refreshing "{existing.get("name")}"...')
    return await run_pipeline(name=existing.get("name"), url=existing.get("website"))