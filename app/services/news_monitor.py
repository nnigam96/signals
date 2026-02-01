"""
Real-time News Monitor Service

Polls Firecrawl for technical news across domains and streams updates.
"""
import asyncio
import logging
import json
from datetime import datetime, timezone
from typing import AsyncGenerator
from dataclasses import dataclass, asdict

from app.pipeline.firecrawl import search_web, agent_deep_dive

logger = logging.getLogger(__name__)

# Domains to monitor
TECH_DOMAINS = [
    {
        "name": "AI & Machine Learning",
        "queries": [
            "AI news today breaking",
            "OpenAI Anthropic Google AI announcement",
            "LLM breakthrough research"
        ]
    },
    {
        "name": "Developer Tools",
        "queries": [
            "developer tools startup funding news",
            "GitHub Vercel Supabase announcement",
            "new programming framework release"
        ]
    },
    {
        "name": "Cloud & Infrastructure",
        "queries": [
            "AWS Azure GCP announcement today",
            "cloud infrastructure startup news",
            "Kubernetes Docker release"
        ]
    },
    {
        "name": "Cybersecurity",
        "queries": [
            "cybersecurity breach news today",
            "security vulnerability disclosure",
            "zero-day exploit announcement"
        ]
    },
    {
        "name": "Fintech",
        "queries": [
            "fintech startup funding news",
            "Stripe payments announcement",
            "crypto regulation news"
        ]
    }
]


@dataclass
class NewsItem:
    """A single news item."""
    id: str
    domain: str
    headline: str
    summary: str
    source: str
    timestamp: str
    relevance: str  # "high", "medium", "low"

    def to_dict(self):
        return asdict(self)


class NewsMonitor:
    """Background service that monitors news across tech domains."""

    def __init__(self):
        self.running = False
        self.latest_news: list[NewsItem] = []
        self.subscribers: list[asyncio.Queue] = []
        self._task = None

    async def start(self):
        """Start the background polling service."""
        if self.running:
            return
        self.running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("[news_monitor] Started background monitoring")

    async def stop(self):
        """Stop the background service."""
        self.running = False
        if self._task:
            self._task.cancel()
        logger.info("[news_monitor] Stopped")

    def subscribe(self) -> asyncio.Queue:
        """Subscribe to news updates. Returns a queue that receives news items."""
        queue = asyncio.Queue()
        self.subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        """Unsubscribe from updates."""
        if queue in self.subscribers:
            self.subscribers.remove(queue)

    async def _broadcast(self, item: NewsItem):
        """Send news item to all subscribers."""
        for queue in self.subscribers:
            await queue.put(item)

    async def _poll_loop(self):
        """Main polling loop - cycles through domains."""
        poll_interval = 30  # seconds between domain checks
        domain_index = 0

        while self.running:
            try:
                domain = TECH_DOMAINS[domain_index % len(TECH_DOMAINS)]
                logger.info(f"[news_monitor] Scanning: {domain['name']}")

                # Pick a random query from the domain
                import random
                query = random.choice(domain["queries"])

                # Use Firecrawl search with structured output
                results = await search_web(f"{query} {datetime.now().strftime('%Y')}", limit=3, return_dicts=True)

                for i, result in enumerate(results):
                    title = result.get("title", "") if isinstance(result, dict) else ""
                    description = result.get("description", "") if isinstance(result, dict) else str(result)
                    url = result.get("url", "") if isinstance(result, dict) else ""

                    if title or (description and len(description) > 20):
                        # Create news item
                        item = NewsItem(
                            id=f"{domain_index}-{i}-{datetime.now().timestamp()}",
                            domain=domain["name"],
                            headline=title or self._extract_headline(description),
                            summary=description[:300] + "..." if len(description) > 300 else description,
                            source=url or "Firecrawl Search",
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            relevance=self._score_relevance(title, description)
                        )

                        self.latest_news.append(item)
                        # Keep only last 50 items
                        if len(self.latest_news) > 50:
                            self.latest_news = self.latest_news[-50:]

                        # Broadcast to subscribers
                        await self._broadcast(item)

                domain_index += 1
                await asyncio.sleep(poll_interval)

            except Exception as e:
                logger.error(f"[news_monitor] Poll error: {e}")
                await asyncio.sleep(10)

    def _extract_headline(self, text: str) -> str:
        """Extract a headline from markdown text."""
        lines = text.strip().split("\n")
        for line in lines:
            line = line.strip()
            # Skip empty lines and images
            if not line or line.startswith("!") or line.startswith("["):
                continue
            # Remove markdown formatting
            line = line.lstrip("#").strip()
            line = line.replace("**", "").replace("*", "")
            if len(line) > 10:
                return line[:150] + "..." if len(line) > 150 else line
        return "News Update"

    def _score_relevance(self, title: str, description: str) -> str:
        """Score news relevance based on keywords."""
        text = f"{title} {description}".lower()

        high_keywords = ["breaking", "announces", "launches", "acquired", "raises",
                         "billion", "million", "funding", "ipo", "breach", "vulnerability"]
        medium_keywords = ["release", "update", "new", "partnership", "expansion",
                           "hiring", "growth", "startup"]

        if any(kw in text for kw in high_keywords):
            return "high"
        if any(kw in text for kw in medium_keywords):
            return "medium"
        return "low"


# Global instance
news_monitor = NewsMonitor()


async def stream_news() -> AsyncGenerator[str, None]:
    """
    Generator that yields news items as SSE events.
    Used by the streaming endpoint.
    """
    # Ensure monitor is running
    if not news_monitor.running:
        await news_monitor.start()

    # Subscribe to updates
    queue = news_monitor.subscribe()

    try:
        # First, send any recent news
        for item in news_monitor.latest_news[-5:]:
            yield f"data: {json.dumps(item.to_dict())}\n\n"

        # Then stream new items as they arrive
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=60)
                yield f"data: {json.dumps(item.to_dict())}\n\n"
            except asyncio.TimeoutError:
                # Send keepalive
                yield f"data: {json.dumps({'type': 'keepalive', 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"

    finally:
        news_monitor.unsubscribe(queue)
