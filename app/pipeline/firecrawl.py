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

async def _find_company_url(name: str) -> str:
    """Helper: Googles the company name to find the URL."""
    async with httpx.AsyncClient(timeout=30) as client:
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
    return ""

async def search_web(query: str, limit: int = 5) -> list[str]:
    """Basic search that returns a list of markdown snippets."""
    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(
            f"{FIRECRAWL_BASE}/search",
            headers=_headers(),
            json={"query": query, "limit": limit},
        )
    if res.status_code != 200:
        logger.error(f"[firecrawl] Search failed for '{query}': {res.status_code}")
        return []
    
    data = res.json()
    return [item.get("markdown", "") for item in data.get("data", [])]

async def scrape_url(url: str) -> str:
    """Scrapes a specific URL to get full page markdown."""
    if not url: return ""
    
    async with httpx.AsyncClient(timeout=45) as client:
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

async def agent_deep_dive(query: str, schema: dict | None = None) -> dict[str, Any]:
    """
    Autonomous Agent: Uses Firecrawl v2 to navigate multiple pages
    and find specific, hard-to-get details (Pricing, API docs, Team).
    """
    logger.info(f"[firecrawl] 🤖 Agent executing mission: '{query}'")
    
    payload = {
        "prompt": query,
        "model": "spark-1-pro", # Uses the 'Smart' model for reasoning
        "strictConstrainToURLs": False # Allow it to follow links
    }
    
    if schema:
        payload["schema"] = schema

    async with httpx.AsyncClient(timeout=120) as client:
        try:
            res = await client.post(
                FIRECRAWL_AGENT_URL,
                headers=_headers(),
                json=payload
            )
            
            if res.status_code != 200:
                logger.error(f"[firecrawl] Agent failed: {res.text}")
                return {}
                
            data = res.json()
            
            # If successful, 'data' usually contains the structured fields requested in schema
            if data.get("success") and "data" in data:
                return data["data"]
                
            return {}
            
        except Exception as e:
            logger.error(f"[firecrawl] Agent exception: {e}")
            return {}

async def crawl_company(name_or_url: str) -> dict[str, Any]:
    """
    The Main Entry Point.
    1. If input is name, find URL.
    2. Scrape Homepage (Full Text).
    3. Search for News/About (Snippets).
    4. Combine for RAG.
    """
    logger.info(f"[firecrawl] Starting standard crawl for: {name_or_url}")
    
    # Step 1: Resolve URL
    target_url = name_or_url
    if not name_or_url.startswith("http"):
        target_url = await _find_company_url(name_or_url)
        if not target_url:
             return {"url": "", "raw": "", "error": "Could not find URL"}
    
    # Step 2: Parallel Execution
    # We want the FULL homepage (for RAG context) and snippets for news
    tasks = [
        scrape_url(target_url),                                      # Task 0: Homepage
        search_web(f"{name_or_url} latest news funding 2025 2026"),  # Task 1: News
        search_web(f"{name_or_url} competitors and pricing"),        # Task 2: Market info
    ]
    
    results = await asyncio.gather(*tasks)
    homepage_md = results[0]
    news_list = results[1]
    market_list = results[2]

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
        "raw": full_context  # <--- RAG uses this
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

if __name__ == "__main__":
    # Manual test block
    import sys
    from dotenv import load_dotenv
    load_dotenv()
    
    if len(sys.argv) > 1:
        target = sys.argv[1]
        print(f"Running agent deep dive for {target}...")
        
        # Test the deep dive specifically
        schema = {"properties": {"price": {"type": "string"}}}
        res = asyncio.run(agent_deep_dive(f"Find the price of {target}", schema))
        print(json.dumps(res, indent=2))