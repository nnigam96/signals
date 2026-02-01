"""
Test the Lovable schema formatter.

Usage:
    python scripts/test_formatter.py [company_name]
"""
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.pipeline.orchestrator import run_pipeline
from app.pipeline.mongodb import connect_db, get_company
from app.services.formatter import format_pipeline_output, format_search_results


def print_json(data: dict, title: str):
    """Pretty print JSON with title."""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print('=' * 60)
    # Remove _raw for cleaner output
    clean = {k: v for k, v in data.items() if k != '_raw'}
    print(json.dumps(clean, indent=2, default=str))


async def test_single_company(name: str):
    """Run pipeline and show formatted output."""
    print(f"\n🚀 Running pipeline for: {name}")
    print("   (This may take 30-90 seconds...)\n")

    connect_db()
    result = await run_pipeline(name=name)

    # Show formatted company
    print_json(result.get("company", {}), "COMPANY (Lovable Schema)")

    # Show signals
    signals = result.get("signals", [])
    if signals:
        print_json({"signals": signals}, f"SIGNALS ({len(signals)} detected)")
    else:
        print("\n📡 No signals detected")

    # Show meta
    print_json(result.get("_meta", {}), "PIPELINE METADATA")

    return result


def test_existing_company(slug: str):
    """Format an existing company from DB."""
    connect_db()
    raw = get_company(slug)

    if not raw:
        print(f"Company '{slug}' not found in database")
        return None

    formatted = format_pipeline_output(raw)
    print_json(formatted.get("company", {}), f"COMPANY: {raw.get('name')}")
    print_json({"signals": formatted.get("signals", [])}, "SIGNALS")

    return formatted


def test_search_results():
    """Test formatting multiple companies as search results."""
    from app.pipeline.mongodb import list_companies

    connect_db()
    companies = list_companies()[:5]  # Get up to 5 companies

    if not companies:
        print("No companies in database")
        return

    results = format_search_results(
        companies,
        query="test query",
        search_duration_ms=1234
    )

    print_json(results, "SEARCH RESULTS (Lovable Schema)")

    # Summary
    print(f"\n📊 Summary:")
    print(f"   Total companies: {results['metadata']['totalMatches']}")
    print(f"   Signal groups: {list(results['signals'].keys())}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]

        if arg == "--existing":
            # Format existing company by slug
            slug = sys.argv[2] if len(sys.argv) > 2 else "stripe"
            test_existing_company(slug)
        elif arg == "--search":
            # Test search results format
            test_search_results()
        else:
            # Run full pipeline
            asyncio.run(test_single_company(arg))
    else:
        print("Usage:")
        print("  python scripts/test_formatter.py <company_name>  # Run full pipeline")
        print("  python scripts/test_formatter.py --existing <slug>  # Format existing")
        print("  python scripts/test_formatter.py --search  # Test search results")
