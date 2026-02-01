"""
Pipeline Orchestrator

Coordinates the parallel execution of:
1. Web crawling (homepage + news)
2. Document parsing (PDFs)
3. Agent Swarm (specialized deep-dives)
4. LLM Analysis
5. RAG Embedding
6. Database Storage
"""
import asyncio
import logging
import time
import json
from datetime import datetime, timezone
from typing import Any

from app.pipeline.firecrawl import crawl_company, agent_deep_dive
from app.pipeline.reducto import parse_document
from app.pipeline.openrouter import analyze_company
from app.pipeline.mongodb import (
    store_company, get_company, store_snapshot,
    make_slug, record_metric_history
)
from app.pipeline.rag import process_and_store_knowledge
from app.services.formatter import format_pipeline_output

logger = logging.getLogger(__name__)


# =============================================================================
# AGENT SWARM CONFIGURATION
# =============================================================================
# Each agent is a specialist that hunts for specific intelligence signals.
# They run in parallel with the main crawl for maximum speed.

AGENT_MISSIONS = [
    {
        "name": "talent_scout",
        "topic": "hiring_velocity",
        "search_query": "{name} careers jobs open positions",
        "prompt": (
            "Navigate to the careers or jobs page. "
            "Count the total number of open positions. "
            "Identify the top 3 departments that are hiring the most. "
            "Determine if hiring is aggressive, active, slow, or frozen."
        ),
        "schema": {
            "type": "object",
            "properties": {
                "open_roles_count": {
                    "type": "integer",
                    "description": "Total number of open job positions"
                },
                "top_departments": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Top 3 departments with most openings"
                },
                "hiring_status": {
                    "type": "string",
                    "enum": ["Aggressive", "Active", "Slow", "Freeze"],
                    "description": "Overall hiring velocity assessment"
                }
            },
            "required": ["hiring_status"]
        }
    },
    {
        "name": "tech_auditor",
        "topic": "dev_velocity",
        "search_query": "{name} changelog api documentation updates",
        "prompt": (
            "Find the developer changelog, release notes, or API documentation. "
            "Extract the date of the most recent update or release. "
            "Determine how frequently they ship updates (daily, weekly, monthly, or stale)."
        ),
        "schema": {
            "type": "object",
            "properties": {
                "last_update_date": {
                    "type": "string",
                    "description": "Date of most recent update (YYYY-MM-DD or descriptive)"
                },
                "update_frequency": {
                    "type": "string",
                    "enum": ["Daily", "Weekly", "Monthly", "Stale (>3mo)"],
                    "description": "How often they release updates"
                },
                "latest_feature": {
                    "type": "string",
                    "description": "Name or description of the latest feature/update"
                }
            },
            "required": ["update_frequency"]
        }
    },
    {
        "name": "pricing_analyst",
        "topic": "pricing_model",
        "search_query": "{name} pricing plans cost",
        "prompt": (
            "Navigate to the pricing page. "
            "Check if there is a free tier or free trial. "
            "Check if the Enterprise tier requires 'Contact Sales'. "
            "Find the lowest paid plan price if visible. "
            "Determine if they follow PLG (product-led growth), Enterprise-only, or Hybrid model."
        ),
        "schema": {
            "type": "object",
            "properties": {
                "has_free_tier": {
                    "type": "boolean",
                    "description": "Whether a free tier or free trial exists"
                },
                "is_enterprise_opaque": {
                    "type": "boolean",
                    "description": "Whether Enterprise pricing requires contacting sales"
                },
                "lowest_paid_price": {
                    "type": "number",
                    "description": "Lowest visible paid plan price per month in USD"
                },
                "pricing_strategy": {
                    "type": "string",
                    "enum": ["PLG", "Hybrid", "Enterprise-Only"],
                    "description": "Overall go-to-market pricing strategy"
                }
            },
            "required": ["has_free_tier"]
        }
    }
]


# =============================================================================
# MAIN PIPELINE
# =============================================================================

async def run_pipeline(
    name: str | None = None,
    url: str | None = None,
    document_base64: str | None = None,
    document_url: str | None = None,
) -> dict[str, Any]:
    """
    Main pipeline: Parallel Agent Swarm + Analysis + RAG + Storage

    Flow:
    1. Launch all ingestion tasks in parallel:
       - Homepage crawl (web + news)
       - Document parse (if provided)
       - Agent swarm (3 specialist agents)
    2. Wait for all to complete
    3. Merge agent findings into context
    4. Run LLM analysis + RAG embedding in parallel
    5. Store to MongoDB

    Args:
        name: Company name to research
        url: Company website URL (optional if name provided)
        document_base64: Base64 encoded document (pitch deck, etc.)
        document_url: URL to document

    Returns:
        Complete company profile dict stored in MongoDB
    """
    start = time.time()
    identifier = name or url or "document"
    logger.info(f"[pipeline] 🚀 Starting Swarm Pipeline for: {identifier}")

    # =========================================================================
    # STEP 1: Parallel Ingestion (Web + Docs + Agent Swarm)
    # =========================================================================
    ingest_tasks = []

    # Task 0: Main Web Crawl (Homepage + News + Market)
    if url or name:
        logger.info("[pipeline] 📡 Queuing homepage crawl...")
        ingest_tasks.append(asyncio.create_task(
            crawl_company(url or name),
            name="crawl"
        ))
    else:
        ingest_tasks.append(asyncio.create_task(
            asyncio.sleep(0, result={"raw": ""}),
            name="crawl_noop"
        ))

    # Task 1: Document Parse (PDFs via Reducto)
    if document_base64 or document_url:
        logger.info("[pipeline] 📄 Queuing document parse...")
        ingest_tasks.append(asyncio.create_task(
            parse_document(document_base64 or document_url),
            name="document"
        ))
    else:
        ingest_tasks.append(asyncio.create_task(
            asyncio.sleep(0, result=None),
            name="document_noop"
        ))

    # Tasks 2..N: Agent Swarm (Deep Dives)
    agent_indices = []
    if name:
        for i, mission in enumerate(AGENT_MISSIONS):
            logger.info(f"[pipeline] 🕵️ Spawning Agent: {mission['name']}")

            # Construct the full query for the agent
            full_query = f"{mission['search_query'].format(name=name)}. {mission['prompt']}"

            task = asyncio.create_task(
                agent_deep_dive(full_query, mission["schema"]),
                name=f"agent_{mission['name']}"
            )
            ingest_tasks.append(task)

            # Track index: offset by 2 (0=Web, 1=Doc)
            agent_indices.append((2 + i, mission))

    # Wait for ALL ingestion tasks
    logger.info(f"[pipeline] ⏳ Waiting for {len(ingest_tasks)} parallel tasks...")
    results = await asyncio.gather(*ingest_tasks, return_exceptions=True)

    # =========================================================================
    # STEP 2: Unpack and Merge Results
    # =========================================================================

    # Unpack web data
    web_data = results[0]
    if isinstance(web_data, Exception):
        logger.error(f"[pipeline] ❌ Web crawl failed: {web_data}")
        web_data = {"raw": "", "error": str(web_data)}

    # Unpack document data
    document_data = results[1]
    if isinstance(document_data, Exception):
        logger.error(f"[pipeline] ❌ Doc parse failed: {document_data}")
        document_data = None

    # Process Agent Results and merge into context
    agent_findings_text = ""
    agent_metrics = {}  # Structured data for DB

    for idx, mission in agent_indices:
        agent_result = results[idx]

        if isinstance(agent_result, Exception):
            logger.warning(f"[pipeline] ⚠️ Agent {mission['name']} failed: {agent_result}")
            continue

        if not agent_result:
            logger.warning(f"[pipeline] ⚠️ Agent {mission['name']} returned empty")
            continue

        # Log success
        logger.info(f"[pipeline] ✅ Agent {mission['name']} returned: {list(agent_result.keys()) if isinstance(agent_result, dict) else 'data'}")

        # Format for RAG (append to raw text so LLM sees it)
        agent_findings_text += f"\n\n=== AGENT REPORT: {mission['topic'].upper()} ===\n"
        agent_findings_text += json.dumps(agent_result, indent=2)

        # Store structured data for DB
        agent_metrics[mission["topic"]] = agent_result

    # Inject agent findings into web context
    if isinstance(web_data, dict):
        web_data["raw"] = web_data.get("raw", "") + agent_findings_text
        web_data["agent_metrics"] = agent_metrics

    # Determine slug
    temp_name = name or (web_data.get("url", "") if isinstance(web_data, dict) else "") or "unknown"
    if document_data and not name:
        temp_name = "uploaded-doc"
    slug = make_slug(temp_name)

    # =========================================================================
    # STEP 3: Parallel Processing (Analysis + RAG)
    # =========================================================================
    logger.info("[pipeline] 🧠 Starting AI Analysis & RAG Embedding...")

    processing_tasks = []

    # Task A: LLM Analysis
    analysis_task = asyncio.create_task(
        analyze_company(name=name, url=url, web_data=web_data, document_data=document_data),
        name="analysis"
    )
    processing_tasks.append(analysis_task)

    # Task B: RAG Embedding - Web Content (includes agent findings)
    if isinstance(web_data, dict) and web_data.get("raw"):
        processing_tasks.append(asyncio.create_task(
            process_and_store_knowledge(slug, web_data["raw"], "web"),
            name="rag_web"
        ))

    # Task C: RAG Embedding - Document Content
    if document_data and isinstance(document_data, dict) and document_data.get("extracted_text"):
        processing_tasks.append(asyncio.create_task(
            process_and_store_knowledge(slug, document_data["extracted_text"], "document"),
            name="rag_doc"
        ))

    # Wait for processing
    proc_results = await asyncio.gather(*processing_tasks, return_exceptions=True)

    # Unpack analysis
    analysis = proc_results[0]
    if isinstance(analysis, Exception):
        logger.error(f"[pipeline] ❌ AI Analysis failed: {analysis}")
        analysis = {
            "name": temp_name,
            "summary": "Analysis failed",
            "metrics": {"sentiment": "Neutral", "signal_strength": 0}
        }

    logger.info("[pipeline] ✅ Analysis & RAG complete")

    # =========================================================================
    # STEP 4: Persistence
    # =========================================================================
    final_name = analysis.get("name") or temp_name
    now = datetime.now(timezone.utc)

    # Build complete profile
    profile = {
        "name": final_name,
        "slug": slug,
        "description": analysis.get("summary", ""),
        "website": url or analysis.get("website", "") or (web_data.get("url", "") if isinstance(web_data, dict) else ""),
        "crawled_at": now,
        "updated_at": now,
        "watchlist": False,

        # Raw data (for debugging/re-analysis)
        "web_data": {
            "url": web_data.get("url") if isinstance(web_data, dict) else None,
            "raw_length": len(web_data.get("raw", "")) if isinstance(web_data, dict) else 0,
        },
        "document_data": {
            "has_document": document_data is not None,
            "text_length": len(document_data.get("extracted_text", "")) if document_data else 0,
        } if document_data else None,

        # LLM Analysis results
        "analysis": analysis,

        # Agent Swarm results (structured)
        "agent_metrics": agent_metrics,

        # Monitoring config
        "monitoring": {
            "active": False,
            "interval_hours": 24,
            "last_checked": now,
            "next_check": None
        }
    }

    # Store to MongoDB
    logger.info(f"[pipeline] 💾 Storing '{final_name}' to MongoDB...")
    stored = store_company(profile)

    # Store snapshot for historical tracking
    store_snapshot(slug, {
        "analysis": analysis,
        "agent_metrics": agent_metrics,
        "timestamp": now.isoformat()
    })

    # Record metrics to time-series collection
    if analysis.get("metrics"):
        metrics_to_store = {**analysis["metrics"]}
        # Add agent-derived metrics
        if agent_metrics.get("hiring_velocity"):
            metrics_to_store["hiring_status"] = agent_metrics["hiring_velocity"].get("hiring_status")
            metrics_to_store["open_roles"] = agent_metrics["hiring_velocity"].get("open_roles_count")
        if agent_metrics.get("pricing_model"):
            metrics_to_store["has_free_tier"] = agent_metrics["pricing_model"].get("has_free_tier")
        record_metric_history(slug, metrics_to_store)

    elapsed = round(time.time() - start, 1)
    logger.info(f'[pipeline] 🎉 Done: "{final_name}" in {elapsed}s')

    # Format output for Lovable frontend schema
    formatted = format_pipeline_output(stored)
    formatted["_raw"] = stored  # Include raw data for debugging
    formatted["_meta"] = {
        "pipeline_duration_seconds": elapsed,
        "agents_completed": list(agent_metrics.keys()),
    }

    return formatted


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

async def refresh_company(slug: str) -> dict[str, Any] | None:
    """Re-run pipeline for an existing company."""
    existing = get_company(slug)
    if not existing:
        logger.warning(f"[pipeline] Company '{slug}' not found")
        return None

    logger.info(f'[pipeline] 🔄 Refreshing "{existing.get("name")}"...')
    return await run_pipeline(
        name=existing.get("name"),
        url=existing.get("website")
    )


async def run_agents_only(name: str) -> dict[str, Any]:
    """Run only the agent swarm without full pipeline (for testing)."""
    logger.info(f"[pipeline] 🕵️ Running agent swarm only for: {name}")

    tasks = []
    for mission in AGENT_MISSIONS:
        full_query = f"{mission['search_query'].format(name=name)}. {mission['prompt']}"
        tasks.append(agent_deep_dive(full_query, mission["schema"]))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    agent_data = {}
    for i, mission in enumerate(AGENT_MISSIONS):
        result = results[i]
        if isinstance(result, dict) and result:
            agent_data[mission["topic"]] = result
        else:
            agent_data[mission["topic"]] = {"error": str(result) if isinstance(result, Exception) else "empty"}

    return agent_data
