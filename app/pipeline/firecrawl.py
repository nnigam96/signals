"""
Firecrawl Integration Module

Provides web crawling and agentic data extraction using Firecrawl API.
- V1 API: Standard scraping and search
- V2 API: Agentic deep-dive with spark-1-pro model
"""
import asyncio
import logging
import json
import os
import httpx
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

FIRECRAWL_BASE = "https://api.firecrawl.dev/v1"
FIRECRAWL_AGENT_URL = "https://api.firecrawl.dev/v2/agent"


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.firecrawl_api_key}",
        "Content-Type": "application/json",
    }


# =============================================================================
# V2 Agent API - Agentic Deep Dive
# =============================================================================

async def agent_deep_dive(query: str, schema: dict | None = None) -> dict[str, Any]:
    """
    Autonomous Agent: Uses Firecrawl V2 to navigate multiple pages
    and find specific, hard-to-get details (Pricing, API docs, Hiring).

    The V2 API is async:
    1. POST to start agent - returns job ID
    2. GET to poll for results

    Args:
        query: The mission prompt for the agent (e.g., "Find pricing for Stripe")
        schema: Optional JSON schema for structured output

    Returns:
        Structured data dict from the agent, or empty dict on failure
    """
    logger.info(f"[firecrawl] 🤖 Agent mission: '{query[:80]}...'")

    payload = {
        "prompt": query,
        "model": "spark-1-pro",
        "strictConstrainToURLs": False,
    }

    if schema:
        payload["schema"] = schema

    async with httpx.AsyncClient(timeout=180) as client:
        try:
            # Step 1: Start the agent job
            res = await client.post(
                FIRECRAWL_AGENT_URL,
                headers=_headers(),
                json=payload
            )

            if res.status_code != 200:
                logger.error(f"[firecrawl] Agent start failed ({res.status_code}): {res.text[:500]}")
                return {}

            data = res.json()

            # Check if it's an async job (returns ID)
            if data.get("success") and data.get("id") and "data" not in data:
                job_id = data["id"]
                logger.info(f"[firecrawl] Agent job started: {job_id}")

                # Step 2: Poll for results
                result = await _poll_agent_job(client, job_id)
                return result

            # Synchronous response (has data directly)
            if data.get("success") and "data" in data:
                result = data["data"]
                if result:
                    logger.info(f"[firecrawl] ✅ Agent returned data: {list(result.keys()) if isinstance(result, dict) else 'list'}")
                return result

            # Other response formats
            if "result" in data:
                return data["result"]
            if "output" in data:
                return data["output"]

            logger.warning(f"[firecrawl] Agent returned unexpected format: {json.dumps(data)[:300]}")
            return {}

        except httpx.TimeoutException:
            logger.error(f"[firecrawl] Agent timeout after 180s")
            return {}
        except Exception as e:
            logger.error(f"[firecrawl] Agent exception: {e}")
            return {}


async def _poll_agent_job(client: httpx.AsyncClient, job_id: str, max_polls: int = 30, interval: float = 2.0) -> dict:
    """
    Poll for agent job completion.

    Args:
        client: HTTP client
        job_id: The job ID returned from agent start
        max_polls: Maximum number of poll attempts
        interval: Seconds between polls

    Returns:
        Agent result data or empty dict
    """
    poll_url = f"{FIRECRAWL_AGENT_URL}/{job_id}"

    for attempt in range(max_polls):
        try:
            res = await client.get(poll_url, headers=_headers())

            if res.status_code != 200:
                logger.warning(f"[firecrawl] Poll failed ({res.status_code})")
                await asyncio.sleep(interval)
                continue

            data = res.json()
            status = data.get("status", "").lower()

            if status == "completed":
                result = data.get("data") or data.get("result") or data.get("output", {})
                if result:
                    logger.info(f"[firecrawl] ✅ Agent completed: {list(result.keys()) if isinstance(result, dict) else 'data'}")
                return result

            if status in ("failed", "error"):
                logger.error(f"[firecrawl] Agent job failed: {data.get('error', 'unknown')}")
                return {}

            # Still processing
            logger.debug(f"[firecrawl] Agent status: {status} (attempt {attempt + 1}/{max_polls})")
            await asyncio.sleep(interval)

        except Exception as e:
            logger.error(f"[firecrawl] Poll exception: {e}")
            await asyncio.sleep(interval)

    logger.warning(f"[firecrawl] Agent polling timeout after {max_polls} attempts")
    return {}


async def agent_extract(url: str, schema: dict) -> dict[str, Any]:
    """
    Extract structured data from a specific URL using the agent.
    More focused than agent_deep_dive - targets a known URL.
    """
    prompt = f"Extract the following information from {url}"

    payload = {
        "prompt": prompt,
        "model": "spark-1-pro",
        "urls": [url],
        "strictConstrainToURLs": True,
        "schema": schema
    }

    async with httpx.AsyncClient(timeout=120) as client:
        try:
            res = await client.post(FIRECRAWL_AGENT_URL, headers=_headers(), json=payload)
            if res.status_code == 200:
                data = res.json()
                return data.get("data", data.get("result", {}))
            return {}
        except Exception as e:
            logger.error(f"[firecrawl] Extract failed: {e}")
            return {}


# =============================================================================
# V1 API - Standard Crawling
# =============================================================================

async def _find_company_url(name: str) -> str:
    """Helper: Search for the company's official website URL."""
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            res = await client.post(
                f"{FIRECRAWL_BASE}/search",
                headers=_headers(),
                json={"query": f"{name} official website home page", "limit": 1}
            )
            data = res.json()
            results = data.get("data", [])
            if results:
                url = results[0].get("url")
                logger.info(f"[firecrawl] 🎯 Discovered URL for {name}: {url}")
                return url
        except Exception as e:
            logger.error(f"[firecrawl] URL discovery failed: {e}")
    return ""


async def search_web(query: str, limit: int = 5, return_dicts: bool = False) -> list:
    """
    Basic search that returns results from the web.

    Args:
        query: Search query
        limit: Max results to return
        return_dicts: If True, returns list of dicts with url/title/description.
                      If False, returns list of formatted strings for backwards compat.
    """
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            res = await client.post(
                f"{FIRECRAWL_BASE}/search",
                headers=_headers(),
                json={"query": query, "limit": limit},
            )
            if res.status_code != 200:
                logger.error(f"[firecrawl] Search failed for '{query}': {res.status_code}")
                return []

            data = res.json()
            items = data.get("data", [])

            if return_dicts:
                return items

            # Return formatted strings (title + description) for backwards compat
            results = []
            for item in items:
                title = item.get("title", "")
                desc = item.get("description", "")
                url = item.get("url", "")
                if title or desc:
                    results.append(f"**{title}**\n{desc}\n{url}")
                elif item.get("markdown"):
                    results.append(item["markdown"])
            return results
        except Exception as e:
            logger.error(f"[firecrawl] Search exception: {e}")
            return []


async def scrape_url(url: str) -> str:
    """Scrapes a specific URL to get full page markdown."""
    if not url:
        return ""

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            res = await client.post(
                f"{FIRECRAWL_BASE}/scrape",
                headers=_headers(),
                json={"url": url, "formats": ["markdown"]},
            )

            if res.status_code != 200:
                logger.error(f"[firecrawl] Scrape failed {url}: {res.status_code}")
                return ""

            data = res.json()
            return data.get("data", {}).get("markdown", "")
        except Exception as e:
            logger.error(f"[firecrawl] Scrape exception for {url}: {e}")
            return ""


async def crawl_company(name_or_url: str) -> dict[str, Any]:
    """
    Main Entry Point for company crawling.

    1. If input is name, find URL via search
    2. Scrape Homepage (Full Text)
    3. Search for News/Market info (Snippets)
    4. Combine all text for RAG

    Returns:
        Dict with 'url', 'homepage', 'news', 'raw' (combined text for RAG)
    """
    logger.info(f"[firecrawl] Starting standard crawl for: {name_or_url}")

    # Step 1: Resolve URL
    target_url = name_or_url
    if not name_or_url.startswith("http"):
        target_url = await _find_company_url(name_or_url)
        if not target_url:
            logger.warning(f"[firecrawl] Could not find URL for {name_or_url}")
            return {"url": "", "raw": "", "error": "Could not find URL"}

    # Step 2: Parallel Execution - Homepage + News + Market
    tasks = [
        scrape_url(target_url),
        search_web(f"{name_or_url} latest news funding 2025 2026"),
        search_web(f"{name_or_url} competitors and pricing"),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    homepage_md = results[0] if not isinstance(results[0], Exception) else ""
    news_list = results[1] if not isinstance(results[1], Exception) else []
    market_list = results[2] if not isinstance(results[2], Exception) else []

    # Combine all text for the "Knowledge Engine"
    full_context = f"SOURCE: {target_url}\n\n=== HOMEPAGE ===\n{homepage_md}\n\n"
    full_context += "=== NEWS ===\n" + "\n---\n".join(news_list) + "\n\n"
    full_context += "=== MARKET ===\n" + "\n---\n".join(market_list)

    # Save to local debug file
    _save_debug_content(name_or_url, full_context)

    return {
        "url": target_url,
        "homepage": homepage_md,
        "news": news_list,
        "raw": full_context
    }


def _save_debug_content(name: str, content: str):
    """Helper to save crawled content to disk for inspection."""
    try:
        os.makedirs("crawled_data", exist_ok=True)
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip().replace(" ", "_")
        filename = f"crawled_data/{safe_name}.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"[firecrawl] 💾 Saved crawl content to {filename}")
    except Exception as e:
        logger.error(f"[firecrawl] Failed to save debug file: {e}")


# =============================================================================
# CLI Testing
# =============================================================================

if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv()

    async def test_agent():
        target = sys.argv[1] if len(sys.argv) > 1 else "Stripe"
        print(f"Testing agent deep dive for: {target}")

        schema = {
            "type": "object",
            "properties": {
                "has_free_tier": {"type": "boolean"},
                "pricing_model": {"type": "string"}
            }
        }

        result = await agent_deep_dive(
            f"{target} pricing plans. Navigate to the pricing page and find if there is a free tier.",
            schema
        )
        print(json.dumps(result, indent=2))

    asyncio.run(test_agent())
