#!/usr/bin/env python3
"""
Signals Intelligence API Demo Script

Demonstrates backend capabilities without requiring frontend.
Run with: python scripts/demo.py [--server URL]
"""
import argparse
import asyncio
import json
import sys
import time
from datetime import datetime

try:
    import httpx
except ImportError:
    print("Installing httpx...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx", "-q"])
    import httpx


# =============================================================================
# CONFIG
# =============================================================================

DEFAULT_SERVER = "http://localhost:8000"
COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "red": "\033[91m",
    "cyan": "\033[96m",
    "magenta": "\033[95m",
}


def c(text: str, color: str) -> str:
    """Colorize text."""
    return f"{COLORS.get(color, '')}{text}{COLORS['reset']}"


def header(text: str):
    """Print section header."""
    print(f"\n{c('=' * 60, 'blue')}")
    print(c(f"  {text}", 'bold')}")
    print(c('=' * 60, 'blue')}\n")


def success(text: str):
    print(f"{c('[OK]', 'green')} {text}")


def info(text: str):
    print(f"{c('[INFO]', 'cyan')} {text}")


def warn(text: str):
    print(f"{c('[WARN]', 'yellow')} {text}")


def error(text: str):
    print(f"{c('[ERROR]', 'red')} {text}")


def json_preview(data: dict, max_lines: int = 15):
    """Pretty print JSON with line limit."""
    formatted = json.dumps(data, indent=2)
    lines = formatted.split('\n')
    if len(lines) > max_lines:
        print('\n'.join(lines[:max_lines]))
        print(c(f"  ... ({len(lines) - max_lines} more lines)", 'yellow'))
    else:
        print(formatted)


# =============================================================================
# API TESTS
# =============================================================================

async def test_health(client: httpx.AsyncClient, base_url: str) -> bool:
    """Test health endpoint."""
    header("1. Health Check")
    try:
        r = await client.get(f"{base_url}/api/health")
        data = r.json()
        success(f"Server: {data.get('service')}")
        success(f"Status: {data.get('status')}")
        success(f"Time: {data.get('timestamp')}")
        return True
    except Exception as e:
        error(f"Health check failed: {e}")
        return False


async def test_analyze_company(client: httpx.AsyncClient, base_url: str, company: str) -> dict | None:
    """Run full pipeline analysis on a company."""
    header(f"2. Analyze Company: {company}")
    info("Running pipeline (this may take 30-60 seconds)...")

    try:
        start = time.time()
        r = await client.post(
            f"{base_url}/api/analyze",
            json={"name": company},
            timeout=120
        )
        elapsed = time.time() - start
        data = r.json()

        if data.get("success"):
            success(f"Analysis complete in {elapsed:.1f}s")

            company_data = data.get("data", {}).get("company", {})
            signals = data.get("data", {}).get("signals", [])

            print(f"\n  {c('Company:', 'bold')} {company_data.get('name')}")
            print(f"  {c('Sector:', 'bold')} {company_data.get('sector')}")
            print(f"  {c('Signal:', 'bold')} {company_data.get('signal')} ({company_data.get('signalStrength')})")
            print(f"  {c('Employees:', 'bold')} {company_data.get('employees')}")

            if signals:
                print(f"\n  {c('Detected Signals:', 'bold')}")
                for sig in signals[:3]:
                    print(f"    - {sig.get('type')}: {sig.get('headline')}")

            return data.get("data")
        else:
            error(f"Analysis failed: {data.get('error')}")
            return None

    except httpx.TimeoutException:
        error("Request timed out (pipeline takes too long)")
        return None
    except Exception as e:
        error(f"Analysis error: {e}")
        return None


async def test_highlights(client: httpx.AsyncClient, base_url: str, slug: str = None):
    """Test highlights endpoint."""
    header("3. Company Highlights")

    try:
        if slug:
            r = await client.get(f"{base_url}/api/company/{slug}/highlights")
            data = r.json()

            if "error" in data:
                warn(f"No highlights for {slug}: {data['error']}")
                return

            print(f"  {c('Company:', 'bold')} {data['company']['name']}")

            # Hiring
            hiring = data.get("hiring", {})
            if hiring.get("hasData"):
                growth_icon = {"positive": "+", "negative": "-", "neutral": "~"}.get(hiring["growth"], "~")
                print(f"\n  {c('Hiring:', 'bold')} [{growth_icon}]")
                print(f"    Open Roles: {hiring.get('openRoles', 'N/A')}")
                print(f"    Status: {hiring.get('status')}")
                if hiring.get("topDepartments"):
                    print(f"    Top Depts: {', '.join(hiring['topDepartments'])}")

            # Funding
            funding = data.get("funding", {})
            if funding.get("hasData"):
                print(f"\n  {c('Funding:', 'bold')}")
                print(f"    Total Raised: {funding.get('totalRaised', 'N/A')}")
                if funding.get("lastRound"):
                    print(f"    Last Round: {funding['lastRound']}")

            # Signals
            signals = data.get("signals", {})
            print(f"\n  {c('Growth Signals:', 'bold')} {signals.get('overall', 'neutral').upper()}")
            print(f"    Score: {signals.get('score', 'N/A')}/100")
            print(f"    Sentiment: {signals.get('sentiment', 'neutral')}")

            if signals.get("positive"):
                print(f"\n    {c('Positive:', 'green')}")
                for s in signals["positive"][:3]:
                    print(f"      + {s['message']}")

            if signals.get("negative"):
                print(f"\n    {c('Negative:', 'red')}")
                for s in signals["negative"][:2]:
                    print(f"      - {s['message']}")
        else:
            # Get all highlights
            r = await client.get(f"{base_url}/api/highlights?limit=5")
            data = r.json()

            print(f"  Found {data.get('count', 0)} companies\n")

            for h in data.get("highlights", [])[:5]:
                signals = h.get("signals", {})
                score = signals.get("score", 0) or 0
                overall = signals.get("overall", "neutral")

                icon = {"positive": c("+", "green"), "slightly_positive": c("+", "green"),
                        "negative": c("-", "red"), "slightly_negative": c("-", "red"),
                        "neutral": c("~", "yellow")}.get(overall, "~")

                print(f"  [{icon}] {h['company']['name']} ({h['company']['sector']}) - Score: {score}")

    except Exception as e:
        error(f"Highlights error: {e}")


async def test_news_stream(client: httpx.AsyncClient, base_url: str, duration: int = 10):
    """Test news streaming endpoint."""
    header("4. Real-time News Stream")
    info(f"Streaming news for {duration} seconds...")

    try:
        # Start news monitor
        await client.post(f"{base_url}/api/news/start")

        # Get latest news (non-streaming for demo)
        r = await client.get(f"{base_url}/api/news/latest?limit=5")
        data = r.json()

        news = data.get("news", [])
        if news:
            success(f"Got {len(news)} news items")
            print()
            for item in news[:5]:
                relevance = item.get("relevance", "low")
                color = {"high": "green", "medium": "yellow", "low": "reset"}.get(relevance, "reset")

                print(f"  {c('[' + item['domain'] + ']', 'cyan')} {c(item['headline'][:60], color)}")
                print(f"    {item['summary'][:80]}...")
                print(f"    {c(item['source'][:50], 'blue')}")
                print()
        else:
            warn("No news items yet (monitor may still be warming up)")

    except Exception as e:
        error(f"News stream error: {e}")


async def test_vector_scores(client: httpx.AsyncClient, base_url: str, slug: str):
    """Test vector scores endpoint."""
    header("5. Cross-Vector Analysis")

    try:
        info(f"Calculating vector scores for {slug}...")
        r = await client.get(f"{base_url}/api/companies/{slug}/vector-scores", timeout=60)
        data = r.json()

        if data.get("success"):
            success("Vector analysis complete")

            vectors = data.get("crossVectorData", {}).get("vectors", [])
            values = data.get("crossVectorData", {}).get("values", [])

            print(f"\n  {c('Pentagon Scores:', 'bold')}")
            for i, v in enumerate(vectors):
                score = int(values[i] * 100) if i < len(values) else 0
                bar = "#" * (score // 5) + "-" * (20 - score // 5)
                color = "green" if score >= 70 else "yellow" if score >= 40 else "red"
                print(f"    {v['label']:20} [{c(bar, color)}] {score}%")

            print(f"\n  {c('Signal Status:', 'bold')}")
            for sig in data.get("signals", []):
                status_color = "green" if sig["status"] == "active" else "yellow"
                print(f"    {sig['type']:12} {c(sig['status'].upper(), status_color)}")

        else:
            warn(f"Vector scores not available: {data.get('error')}")

    except Exception as e:
        error(f"Vector scores error: {e}")


async def test_search(client: httpx.AsyncClient, base_url: str, query: str):
    """Test search/job system."""
    header("6. Async Search Job")

    try:
        info(f"Starting search job for: {query}")

        # Create job
        r = await client.post(f"{base_url}/api/search", json={"query": query})
        data = r.json()
        job_id = data.get("jobId")

        if not job_id:
            error("Failed to create job")
            return

        success(f"Job created: {job_id[:8]}...")

        # Poll for completion
        for i in range(30):
            await asyncio.sleep(2)
            r = await client.get(f"{base_url}/api/job/{job_id}/status")
            status = r.json()

            progress = status.get("progress", 0)
            state = status.get("status", "unknown")

            print(f"\r  Progress: [{('#' * (progress // 5)):20}] {progress}% - {state}", end="")

            if status.get("isComplete"):
                print()
                break

        # Get results
        r = await client.get(f"{base_url}/api/job/{job_id}/results")
        results = r.json()

        if "error" in results:
            error(f"Job failed: {results['error']}")
        else:
            companies = results.get("companies", [])
            success(f"Found {len(companies)} companies")

            for co in companies[:3]:
                print(f"    - {co.get('name')} ({co.get('sector')})")

    except Exception as e:
        error(f"Search error: {e}")


async def test_companies_list(client: httpx.AsyncClient, base_url: str):
    """List existing companies."""
    header("7. Stored Companies")

    try:
        r = await client.get(f"{base_url}/api/companies")
        data = r.json()

        companies = data.get("companies", [])
        success(f"Found {len(companies)} companies in database")

        if companies:
            print()
            for co in companies[:10]:
                signal = co.get("signal", "none")
                strength = co.get("signalStrength", "")
                print(f"  - {co.get('name'):25} | {co.get('sector'):15} | {signal} ({strength})")

        return companies

    except Exception as e:
        error(f"List error: {e}")
        return []


# =============================================================================
# MAIN
# =============================================================================

async def run_demo(base_url: str, company: str = None, skip_analyze: bool = False):
    """Run full demo sequence."""
    print(c("""
    ╔═══════════════════════════════════════════════════════════╗
    ║          SIGNALS INTELLIGENCE - BACKEND DEMO              ║
    ╚═══════════════════════════════════════════════════════════╝
    """, "cyan"))

    print(f"  Server: {c(base_url, 'blue')}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    async with httpx.AsyncClient() as client:
        # 1. Health check
        if not await test_health(client, base_url):
            error("Server not available. Exiting.")
            return

        # 2. List existing companies
        companies = await test_companies_list(client, base_url)

        # 3. Analyze new company (optional)
        slug = None
        if company and not skip_analyze:
            result = await test_analyze_company(client, base_url, company)
            if result:
                slug = result.get("company", {}).get("id", "").split("-")[0]
                # Use slug from existing companies if available
                for co in companies:
                    if co.get("name", "").lower() == company.lower():
                        slug = co.get("id", "").split("-")[0]
                        break

        # Use first company if no specific one analyzed
        if not slug and companies:
            # Extract slug from first company
            first = companies[0]
            slug = first.get("name", "").lower().replace(" ", "-")

        # 4. Highlights
        await test_highlights(client, base_url, slug)

        # 5. Vector scores (if we have a company)
        if slug:
            await test_vector_scores(client, base_url, slug)

        # 6. News stream
        await test_news_stream(client, base_url)

        # Summary
        header("Demo Complete")
        print(f"""
  {c('Available Endpoints:', 'bold')}

  GET  /api/health                      - Health check
  GET  /api/companies                   - List all companies
  GET  /api/company/{{slug}}              - Get company details
  GET  /api/company/{{slug}}/highlights   - Key metrics & signals
  GET  /api/company/{{slug}}/signals      - Detailed signals
  GET  /api/companies/{{slug}}/vector-scores - Pentagon analysis

  POST /api/analyze                     - Run pipeline on company
  POST /api/search                      - Start async search job
  GET  /api/job/{{id}}/status             - Poll job progress
  GET  /api/job/{{id}}/results            - Get job results

  GET  /api/highlights                  - All company highlights
  GET  /api/news/stream                 - SSE news stream
  GET  /api/news/latest                 - Latest news items
  POST /api/news/start                  - Start news monitor

  POST /api/reports/hn                  - Generate HN report
  GET  /api/reports/hn/search           - Search HN discussions
        """)


def main():
    parser = argparse.ArgumentParser(description="Signals Intelligence Demo")
    parser.add_argument("--server", "-s", default=DEFAULT_SERVER, help="Server URL")
    parser.add_argument("--company", "-c", help="Company to analyze (e.g., 'Stripe')")
    parser.add_argument("--skip-analyze", action="store_true", help="Skip pipeline analysis")
    args = parser.parse_args()

    asyncio.run(run_demo(args.server, args.company, args.skip_analyze))


if __name__ == "__main__":
    main()
