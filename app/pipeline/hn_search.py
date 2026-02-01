"""
Hacker News Search via Algolia API.

Public API - no authentication required.
Docs: https://hn.algolia.com/api
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

import httpx

logger = logging.getLogger(__name__)

HN_ALGOLIA_BASE = "https://hn.algolia.com/api/v1"


async def search_hn(
    query: str,
    limit: int = 5,
    years_back: int = 2,
) -> list[dict[str, Any]]:
    """
    Search Hacker News discussions via Algolia API.

    Args:
        query: Search keywords (company name, product, etc.)
        limit: Maximum number of results to return (default 5)
        years_back: Filter to discussions from last N years (default 2)

    Returns:
        List of discussion objects with keys:
            - title: Discussion title
            - url: HN discussion URL
            - story_url: External URL if present
            - points: Upvotes
            - num_comments: Comment count
            - author: Username who posted
            - created_at: ISO timestamp
            - objectID: HN item ID
    """
    logger.info(f"[hn] Searching for: '{query}' (last {years_back} years, limit {limit})")

    # Calculate timestamp for N years ago
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=years_back * 365)
    cutoff_timestamp = int(cutoff_date.timestamp())

    params = {
        "query": query,
        "tags": "story",  # Only search stories (not comments)
        "numericFilters": f"created_at_i>{cutoff_timestamp}",
        "hitsPerPage": limit,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.get(
                f"{HN_ALGOLIA_BASE}/search",
                params=params,
            )

        if res.status_code != 200:
            logger.error(f"[hn] Search failed: {res.status_code} - {res.text[:200]}")
            return []

        data = res.json()
        hits = data.get("hits", [])

        results = []
        for hit in hits[:limit]:
            result = {
                "title": hit.get("title", ""),
                "url": f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                "story_url": hit.get("url", ""),
                "points": hit.get("points", 0),
                "num_comments": hit.get("num_comments", 0),
                "author": hit.get("author", ""),
                "created_at": hit.get("created_at", ""),
                "objectID": hit.get("objectID", ""),
            }
            results.append(result)

        logger.info(f"[hn] Found {len(results)} discussions for '{query}'")
        return results

    except Exception as e:
        logger.error(f"[hn] Search exception: {e}")
        return []


async def get_hn_comments(object_id: str, limit: int = 20) -> list[dict[str, Any]]:
    """
    Fetch top comments for a specific HN story.

    Args:
        object_id: HN story ID
        limit: Max comments to return

    Returns:
        List of comment objects with text, author, points
    """
    logger.info(f"[hn] Fetching comments for story {object_id}")

    params = {
        "tags": f"comment,story_{object_id}",
        "hitsPerPage": limit,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.get(
                f"{HN_ALGOLIA_BASE}/search",
                params=params,
            )

        if res.status_code != 200:
            logger.error(f"[hn] Comments fetch failed: {res.status_code}")
            return []

        data = res.json()
        hits = data.get("hits", [])

        comments = []
        for hit in hits[:limit]:
            comment = {
                "text": hit.get("comment_text", ""),
                "author": hit.get("author", ""),
                "points": hit.get("points", 0),
                "created_at": hit.get("created_at", ""),
            }
            comments.append(comment)

        logger.info(f"[hn] Retrieved {len(comments)} comments for story {object_id}")
        return comments

    except Exception as e:
        logger.error(f"[hn] Comments exception: {e}")
        return []


async def search_hn_with_context(
    query: str,
    limit: int = 5,
    comments_per_story: int = 10,
) -> list[dict[str, Any]]:
    """
    Search HN and fetch top comments for each result.
    Runs comment fetches in parallel for performance.

    Returns:
        List of discussions with embedded comments
    """
    discussions = await search_hn(query, limit=limit)

    if not discussions:
        return []

    # Fetch comments in parallel
    comment_tasks = [
        get_hn_comments(d["objectID"], limit=comments_per_story)
        for d in discussions
    ]

    all_comments = await asyncio.gather(*comment_tasks, return_exceptions=True)

    # Merge comments into discussions
    for i, discussion in enumerate(discussions):
        if isinstance(all_comments[i], list):
            discussion["comments"] = all_comments[i]
        else:
            discussion["comments"] = []
            logger.warning(f"[hn] Failed to fetch comments for {discussion['objectID']}")

    return discussions


if __name__ == "__main__":
    # Manual test
    import sys
    from dotenv import load_dotenv
    load_dotenv()

    query = sys.argv[1] if len(sys.argv) > 1 else "Anthropic"
    print(f"Searching HN for: {query}")

    results = asyncio.run(search_hn_with_context(query, limit=3))

    for r in results:
        print(f"\n{'='*60}")
        print(f"Title: {r['title']}")
        print(f"URL: {r['url']}")
        print(f"Points: {r['points']} | Comments: {r['num_comments']}")
        print(f"Date: {r['created_at']}")
        if r.get("comments"):
            print(f"\nTop {len(r['comments'])} comments:")
            for c in r["comments"][:3]:
                text = c["text"][:150] + "..." if len(c["text"]) > 150 else c["text"]
                print(f"  - {c['author']}: {text}")
