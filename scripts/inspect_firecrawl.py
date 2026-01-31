import asyncio
import json
import os
import sys
import httpx
from dotenv import load_dotenv

# Fix path to import from app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
BASE_URL = "https://api.firecrawl.dev/v1"

def _headers():
    return {
        "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
        "Content-Type": "application/json",
    }

async def test_search(query: str, limit: int = 5):
    """Test the search endpoint."""
    print(f"\n=== TESTING SEARCH ===")
    print(f"Query: {query}")
    print(f"Limit: {limit}")
    
    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(
            f"{BASE_URL}/search",
            headers=_headers(),
            json={"query": query, "limit": limit}
        )
    
    if res.status_code != 200:
        print(f"Search Error {res.status_code}: {res.text}")
        return None
    
    data = res.json()
    
    # Save raw response
    output_file = "firecrawl_search_debug.json"
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Raw response saved to: {output_file}")
    
    results = data.get("data", [])
    print(f"\nResults found: {len(results)}")
    
    for i, item in enumerate(results[:3], 1):
        print(f"\n  Result {i}:")
        print(f"    URL: {item.get('url', 'N/A')}")
        print(f"    Title: {item.get('title', 'N/A')}")
        markdown = item.get('markdown', '')
        if markdown:
            print(f"    Preview: {markdown[:150]}...")
    
    return data

async def test_scrape(url: str):
    """Test the scrape endpoint."""
    print(f"\n=== TESTING SCRAPE ===")
    print(f"URL: {url}")
    
    async with httpx.AsyncClient(timeout=45) as client:
        res = await client.post(
            f"{BASE_URL}/scrape",
            headers=_headers(),
            json={"url": url, "formats": ["markdown"]}
        )
    
    if res.status_code != 200:
        print(f"Scrape Error {res.status_code}: {res.text}")
        return None
    
    data = res.json()
    
    # Save raw response
    output_file = "firecrawl_scrape_debug.json"
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Raw response saved to: {output_file}")
    
    scraped_data = data.get("data", {})
    markdown = scraped_data.get("markdown", "")
    
    print(f"\nScraped content length: {len(markdown)} characters")
    if markdown:
        print(f"Preview (first 300 chars):\n{markdown[:300]}...")
    
    # Also save markdown to file
    safe_url = "".join(c for c in url if c.isalnum() or c in ('.', '-', '_', '/')).replace('/', '_')
    md_file = f"firecrawl_scrape_{safe_url[:50]}.md"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(markdown)
    print(f"Markdown saved to: {md_file}")
    
    return data

async def test_find_company_url(name: str):
    """Test finding company URL via search."""
    print(f"\n=== TESTING FIND COMPANY URL ===")
    print(f"Company name: {name}")
    
    query = f"{name} official website home page"
    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(
            f"{BASE_URL}/search",
            headers=_headers(),
            json={"query": query, "limit": 1}
        )
    
    if res.status_code != 200:
        print(f"Search Error {res.status_code}: {res.text}")
        return None
    
    data = res.json()
    results = data.get("data", [])
    
    if results:
        url = results[0].get("url")
        print(f"Found URL: {url}")
        return url
    else:
        print("No URL found")
        return None

async def test_full_crawl(name_or_url: str):
    """Test the full crawl_company workflow."""
    print(f"\n=== TESTING FULL CRAWL ===")
    print(f"Target: {name_or_url}")
    
    # Step 1: Resolve URL
    target_url = name_or_url
    if not name_or_url.startswith("http"):
        print("Step 1: Finding company URL...")
        target_url = await test_find_company_url(name_or_url)
        if not target_url:
            print("Could not find company URL, aborting")
            return None
    else:
        print(f"Step 1: Using provided URL: {target_url}")
    
    # Step 2: Scrape homepage
    print("\nStep 2: Scraping homepage...")
    homepage_data = await test_scrape(target_url)
    homepage_md = ""
    if homepage_data:
        homepage_md = homepage_data.get("data", {}).get("markdown", "")
    
    # Step 3: Search for news
    print("\nStep 3: Searching for news...")
    news_query = f"{name_or_url} latest news funding 2025 2026"
    news_data = await test_search(news_query, limit=3)
    news_list = []
    if news_data:
        news_list = [item.get("markdown", "") for item in news_data.get("data", [])]
    
    # Step 4: Search for market info
    print("\nStep 4: Searching for market info...")
    market_query = f"{name_or_url} competitors and pricing"
    market_data = await test_search(market_query, limit=3)
    market_list = []
    if market_data:
        market_list = [item.get("markdown", "") for item in market_data.get("data", [])]
    
    # Combine results
    full_context = f"SOURCE: {target_url}\n\n=== HOMEPAGE ===\n{homepage_md}\n\n"
    full_context += "=== NEWS ===\n" + "\n---\n".join(news_list) + "\n\n"
    full_context += "=== MARKET ===\n" + "\n---\n".join(market_list)
    
    # Save combined output
    safe_name = "".join(c for c in name_or_url if c.isalnum() or c in (' ', '-', '_')).strip().replace(" ", "_")
    output_file = f"firecrawl_full_crawl_{safe_name}.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(full_context)
    print(f"\nCombined output saved to: {output_file}")
    
    # Summary
    print("\n--- SUMMARY ---")
    print(f"Target URL:      {target_url}")
    print(f"Homepage length: {len(homepage_md)} chars")
    print(f"News snippets:   {len(news_list)}")
    print(f"Market snippets: {len(market_list)}")
    print(f"Total context:   {len(full_context)} chars")
    print("-" * 30)
    
    return {
        "url": target_url,
        "homepage": homepage_md,
        "news": news_list,
        "market": market_list,
        "raw": full_context
    }

async def main():
    if not FIRECRAWL_API_KEY:
        print("Error: FIRECRAWL_API_KEY not found in environment")
        return
    
    # Default target
    target = "Anthropic"
    if len(sys.argv) > 1:
        target = sys.argv[1]
    
    print(f"Testing Firecrawl API for: {target}")
    print("=" * 50)
    
    # Run full crawl test
    result = await test_full_crawl(target)
    
    if result:
        print(f"\nTest complete! Check output files for details.")

if __name__ == "__main__":
    asyncio.run(main())