import asyncio
import logging
import time
import json
from datetime import datetime, timezone
from typing import Any

from app.pipeline.firecrawl import crawl_company, agent_deep_dive
from app.pipeline.reducto import parse_document
from app.pipeline.openrouter import analyze_company
from app.pipeline.mongodb import store_company, get_company, store_snapshot, make_slug, record_metric_history
from app.pipeline.rag import process_and_store_knowledge

logger = logging.getLogger(__name__)

# ─── AGENT MISSIONS CONFIGURATION ─────────────────────────────────────────────
# Defines the specific "Specialist Agents" we spin up for every company.
AGENT_MISSIONS = [
    {
        "name": "talent_scout",
        "topic": "hiring_velocity",
        "search_query": "{name} careers jobs greenhouse lever ashby", 
        "prompt": "Navigate to the careers page. Count the approximate number of open positions. Identify the top 3 departments hiring. Look for keywords like 'Hiring Freeze'.",
        "schema": {
            "type": "object",
            "properties": {
                "open_roles_count": {"type": "integer"},
                "top_departments": {"type": "array", "items": {"type": "string"}},
                "hiring_status": {"type": "string", "enum": ["Aggressive", "Active", "Slow", "Freeze"]}
            },
            "required": ["open_roles_count", "hiring_status"]
        }
    },
    {
        "name": "tech_auditor",
        "topic": "dev_velocity",
        "search_query": "{name} developer changelog api documentation release notes",
        "prompt": "Find the developer changelog or API docs. Extract the date of the most recent update. Determine the update frequency.",
        "schema": {
            "type": "object",
            "properties": {
                "last_update_date": {"type": "string"},
                "update_frequency": {"type": "string", "enum": ["Daily", "Weekly", "Monthly", "Stale (>3mo)"]},
                "latest_feature": {"type": "string"}
            },
            "required": ["last_update_date"]
        }
    },
    {
        "name": "pricing_analyst",
        "topic": "pricing_model",
        "search_query": "{name} pricing plans enterprise cost",
        "prompt": "Navigate to the Pricing page. Check if there is a Free Tier. Check if Enterprise tier says 'Contact Sales'. Find the lowest paid plan price.",
        "schema": {
            "type": "object",
            "properties": {
                "has_free_tier": {"type": "boolean"},
                "is_enterprise_opaque": {"type": "boolean"},
                "lowest_paid_price": {"type": "number"},
                "pricing_strategy": {"type": "string", "enum": ["PLG", "Hybrid", "Enterprise-Only"]}
            },
            "required": ["has_free_tier", "is_enterprise_opaque"]
        }
    }
]

async def run_pipeline(
    name: str | None = None,
    url: str | None = None,
    document_base64: str | None = None,
    document_url: str | None = None,
) -> dict[str, Any]:
    """
    Main pipeline: Crawl (Web) + Agent Swarm + Parse (Doc) -> Analyze (LLM) + Embed (RAG) -> Store (DB).
    Runs ALL ingestion steps in PARALLEL for maximum speed.
    """
    start = time.time()
    identifier = name or url or "document"
    logger.info(f"[pipeline] 🚀 Starting pipeline for: {identifier}")

    # ── Step 1: Parallel Ingestion (Web + Docs + Agents) ──
    ingest_tasks = []

    # Task 0: Main Web Crawl (Homepage)
    if url or name:
        logger.info("[pipeline] Queuing homepage crawl...")
        ingest_tasks.append(asyncio.create_task(crawl_company(url or name)))
    else:
        ingest_tasks.append(asyncio.create_task(asyncio.sleep(0, result={"raw": ""})))

    # Task 1: Document Parse (PDFs)
    if document_base64 or document_url:
        logger.info("[pipeline] Queuing doc parse...")
        ingest_tasks.append(asyncio.create_task(parse_document(document_base64 or document_url)))
    else:
        ingest_tasks.append(asyncio.create_task(asyncio.sleep(0, result=None)))

    # Tasks 2..N: Agent Swarm (Deep Dives)
    # Only launch these if we have a name to search for
    agent_indices = []
    if name:
        for i, mission in enumerate(AGENT_MISSIONS):
            logger.info(f"[pipeline] 🕵️ Spawning Agent: {mission['name']}")
            
            # Construct the query: "Stripe pricing plans enterprise cost. Navigate to..."
            full_query = mission["search_query"].format(name=name) + ". " + mission["prompt"]
            
            task = asyncio.create_task(agent_deep_dive(full_query, mission["schema"]))
            ingest_tasks.append(task)
            
            # Track which index in the results list belongs to which agent
            # Offset is 2 because index 0 is Web, index 1 is Doc
            agent_indices.append((2 + i, mission))

    # Wait for EVERYTHING to finish
    results = await asyncio.gather(*ingest_tasks, return_exceptions=True)
    
    # Unpack Results
    # 1. Web Data
    web_data = results[0]
    if isinstance(web_data, Exception):
        logger.error(f"[pipeline] Web crawl failed: {web_data}")
        web_data = {"error": str(web_data), "raw": ""}
    
    # 2. Document Data
    document_data = results[1]
    if isinstance(document_data, Exception):
        logger.error(f"[pipeline] Doc parse failed: {document_data}")
        document_data = None

    # 3. Process Agent Results
    # We append the agent findings to 'web_data["raw"]' so the LLM sees them.
    # We also prepare them for RAG.
    agent_findings_text = ""
    
    for idx, mission in agent_indices:
        agent_result = results[idx]
        if isinstance(agent_result, Exception) or not agent_result:
            logger.warning(f"[pipeline] Agent {mission['name']} came back empty.")
            continue
            
        # Format the structured JSON back into text for RAG/LLM context
        # e.g. "=== PRICING_MODEL === \n { 'has_free_tier': true ... }"
        formatted_finding = f"\n\n=== AGENT REPORT: {mission['topic'].upper()} ===\n"
        formatted_finding += json.dumps(agent_result, indent=2)
        
        agent_findings_text += formatted_finding

    # Attach agent findings to the main web context
    if isinstance(web_data, dict):
        current_raw = web_data.get("raw", "")
        web_data["raw"] = current_raw + agent_findings_text

    # Determine Company Name & Slug
    temp_name = name or (web_data.get("url") if web_data else "unknown")
    if document_data and not temp_name:
        temp_name = "uploaded-doc"
    slug = make_slug(temp_name)

    # ── Step 2: Parallel Processing (Analysis + RAG) ──
    logger.info("[pipeline] Starting AI Analysis & RAG Embedding...")
    
    processing_tasks = []

    # Task A: OpenRouter Analysis (The "Intelligence")
    analysis_task = asyncio.create_task(analyze_company(
        name=name, url=url, web_data=web_data, document_data=document_data
    ))
    processing_tasks.append(analysis_task)

    # Task B: RAG Embedding (The "Memory")
    
    # 1. Embed Main Web Content
    if web_data and web_data.get("raw"):
        # We use the raw text that now INCLUDES the agent findings
        processing_tasks.append(asyncio.create_task(
            process_and_store_knowledge(slug, web_data["raw"], "web")
        ))

    # 2. Embed Document Content
    if document_data and document_data.get("extracted_text"):
        processing_tasks.append(asyncio.create_task(
            process_and_store_knowledge(slug, document_data["extracted_text"], "document")
        ))

    # Wait for Processing
    proc_results = await asyncio.gather(*processing_tasks, return_exceptions=True)
    
    analysis = proc_results[0]
    if isinstance(analysis, Exception):
        logger.error(f"[pipeline] AI Analysis failed: {analysis}")
        analysis = {"summary": "Analysis failed", "name": temp_name}

    logger.info("[pipeline] ✓ Analysis & RAG complete")

    # ── Step 3: Persistence ──
    final_name = analysis.get("name") or temp_name
    
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
        # Default monitoring to OFF until user enables it
        "monitoring": {"active": False, "interval_hours": 24, "last_checked": now, "next_check": None}
    }

    logger.info(f"[pipeline] Storing '{final_name}' in MongoDB...")
    stored = store_company(profile)
    store_snapshot(slug, {"web_data": web_data, "document_data": document_data, "analysis": analysis})
    
    # Store the calculated metrics in the Time Series collection
    if analysis.get("metrics"):
        record_metric_history(slug, analysis["metrics"])

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