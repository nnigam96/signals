import asyncio
import logging
from typing import Any
import httpx
from app.config import settings

logger = logging.getLogger(__name__)
FIRECRAWL_BASE = "https://api.firecrawl.dev/v1"

def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.firecrawl_api_key}",
        "Content-Type": "application/json",
    }

async def scrape_url(url: str) -> str:
    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(
            f"{FIRECRAWL_BASE}/scrape",
            headers=_headers(),
            json={"url": url, "formats": ["markdown"]},
        )
    if res.status_code != 200:
        logger.error(f"[firecrawl] Scrape failed {url}: {res.text[:100]}")
        return ""
    data = res.json()
    return data.get("data", {}).get("markdown", "")

async def search_web(query: str, limit: int = 5) -> list[str]:
    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(
            f"{FIRECRAWL_BASE}/search",
            headers=_headers(),
            json={"query": query, "limit": limit},
        )
    if res.status_code != 200:
        return []
    data = res.json()
    return [item.get("markdown", "") for item in data.get("data", [])]

async def crawl_company(name_or_url: str) -> dict[str, Any]:
    logger.info(f"[firecrawl] Crawling: {name_or_url}")
    is_url = name_or_url.startswith("http")
    
    homepage_task = scrape_url(name_or_url) if is_url else asyncio.sleep(0, "")
    
    # Determine search term
    term = name_or_url
    if is_url:
        # crude extraction: https://stripe.com -> stripe.com
        term = name_or_url.replace("https://", "").replace("http://", "").split("/")[0]

    # Run searches in parallel
    news_task = search_web(f"{term} latest news funding 2025 2026")
    general_task = search_web(f"{term} company about team product")
    
    results = await asyncio.gather(homepage_task, news_task, general_task)
    homepage, news, general = results

    # Combine into one context blob
    raw = f"HOMEPAGE:\n{homepage}\n\nGENERAL:\n" + "\n".join(general) + "\n\nNEWS:\n" + "\n".join(news)
    
    return {
        "homepage": homepage,
        "news": news,
        "raw": raw
    }