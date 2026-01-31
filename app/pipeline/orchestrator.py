import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

from app.pipeline.firecrawl import crawl_company
from app.pipeline.reducto import parse_document
from app.pipeline.openrouter import analyze_company
from app.pipeline.mongodb import store_company, get_company, store_snapshot, make_slug
from app.pipeline.rag import process_and_store_knowledge  # New RAG import

logger = logging.getLogger(__name__)

async def run_pipeline(
    name: str | None = None,
    url: str | None = None,
    document_base64: str | None = None,
    document_url: str | None = None,
) -> dict[str, Any]:
    """
    Main pipeline: Crawl (Web) + Parse (Doc) -> Analyze (LLM) + Embed (RAG) -> Store (DB).
    Runs ingestion and processing steps in PARALLEL for maximum speed.
    """
    start = time.time()
    identifier = name or url or "document"
    logger.info(f"[pipeline] Starting for: {identifier}")

    # ── Step 1: Parallel Ingestion (Web + Docs) ──
    ingest_tasks = []

    # Task A: Web Crawl
    if url or name:
        logger.info("[pipeline] Queuing web crawl...")
        ingest_tasks.append(asyncio.create_task(crawl_company(url or name)))
    else:
        ingest_tasks.append(asyncio.create_task(asyncio.sleep(0, result={"raw": ""})))

    # Task B: Document Parse
    if document_base64 or document_url:
        logger.info("[pipeline] Queuing doc parse...")
        ingest_tasks.append(asyncio.create_task(parse_document(document_base64 or document_url)))
    else:
        ingest_tasks.append(asyncio.create_task(asyncio.sleep(0, result=None)))

    # Wait for ingestion to finish
    results = await asyncio.gather(*ingest_tasks, return_exceptions=True)
    
    # Unpack results with error handling
    web_data = results[0]
    if isinstance(web_data, Exception):
        logger.error(f"[pipeline] Web crawl failed: {web_data}")
        web_data = {"error": str(web_data), "raw": ""}
    
    document_data = results[1]
    if isinstance(document_data, Exception):
        logger.error(f"[pipeline] Doc parse failed: {document_data}")
        document_data = None

    # Determine Company Name & Slug early for RAG storage
    # We might refine the name after analysis, but we need a slug now for vector storage
    temp_name = name or (web_data.get("url") if web_data else "unknown")
    if document_data and not temp_name:
        temp_name = "uploaded-doc"
    slug = make_slug(temp_name)

    # ── Step 2: Parallel Processing (Analysis + RAG) ──
    # We run the AI Analysis AND the Vector Embedding at the same time.
    logger.info("[pipeline] Starting AI Analysis & RAG Embedding...")
    
    processing_tasks = []

    # Task 1: OpenRouter Analysis (The "Intelligence")
    analysis_task = asyncio.create_task(analyze_company(
        name=name, url=url, web_data=web_data, document_data=document_data
    ))
    processing_tasks.append(analysis_task)

    # Task 2: RAG Embedding (The "Memory")
    # Store Web Data Vectors
    if web_data and web_data.get("raw"):
        processing_tasks.append(asyncio.create_task(
            process_and_store_knowledge(slug, web_data["raw"], "web")
        ))

    # Store Document Data Vectors
    if document_data and document_data.get("extracted_text"):
        processing_tasks.append(asyncio.create_task(
            process_and_store_knowledge(slug, document_data["extracted_text"], "document")
        ))

    # Wait for ALL processing to complete
    # We await here so that when this function returns, the data is searchable.
    proc_results = await asyncio.gather(*processing_tasks, return_exceptions=True)
    
    # The first result is always the analysis (Task 1)
    analysis = proc_results[0]
    if isinstance(analysis, Exception):
        logger.error(f"[pipeline] AI Analysis failed: {analysis}")
        analysis = {"summary": "Analysis failed", "name": temp_name}

    logger.info("[pipeline] ✓ Analysis & RAG complete")

    # ── Step 3: Persistence ──
    # Refine name if the AI found a better one
    final_name = analysis.get("name") or temp_name
    # Update slug if name changed significantly, but usually safer to keep the original
    # or ensure your RAG/DB logic handles aliases. For hackathon, stick to original slug
    # or update carefully. We'll stick to the generated one for consistency.

    now = datetime.now(timezone.utc)
    profile = {
        "name": final_name,
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

    logger.info(f"[pipeline] Storing '{final_name}' in MongoDB...")
    stored = store_company(profile)
    store_snapshot(slug, {"web_data": web_data, "document_data": document_data, "analysis": analysis})

    elapsed = round(time.time() - start, 1)
    logger.info(f'[pipeline] ✅ Done: "{final_name}" in {elapsed}s')
    return stored

async def refresh_company(slug: str) -> dict[str, Any] | None:
    """Re-run pipeline for an existing company."""
    existing = get_company(slug)
    if not existing:
        return None
    logger.info(f'[pipeline] Refreshing "{existing.get("name")}"...')
    return await run_pipeline(name=existing.get("name"), url=existing.get("website"))