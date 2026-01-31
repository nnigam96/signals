"""
Quick smoke test — run this after filling in .env to verify everything works.
Usage: python scripts/test_pipeline.py
"""
import asyncio
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


async def main():
    from app.config import settings
    from app.pipeline.mongodb import connect_db
    from app.pipeline.orchestrator import run_pipeline

    # Check keys
    print("\n🔑 Checking API keys...")
    checks = {
        "FIRECRAWL": bool(settings.firecrawl_api_key),
        "REDUCTO": bool(settings.reducto_api_key),
        "OPENROUTER": bool(settings.openrouter_api_key),
        "MONGODB": bool(settings.mongodb_uri and "mongodb" in settings.mongodb_uri),
    }
    for name, ok in checks.items():
        print(f"   {'✅' if ok else '❌'} {name}")

    if not all(checks.values()):
        print("\n❌ Missing API keys. Fill in .env first.\n")
        return

    # Connect DB
    print("\n📡 Connecting to MongoDB...")
    connect_db()

    # Run pipeline
    test_company = "Anthropic"
    print(f"\n🚀 Running pipeline for: {test_company}")
    print("   (This will take 15-30 seconds — real API calls)\n")

    try:
        profile = await run_pipeline(name=test_company)

        # Show results
        analysis = profile.get("analysis", {})
        print(f"\n{'═' * 50}")
        print(f"Company: {profile.get('name')}")
        print(f"Summary: {analysis.get('summary', 'N/A')[:200]}")
        print(f"PMF Score: {analysis.get('pmf_score', 'N/A')}")
        print(f"Competitors: {', '.join(analysis.get('competitors', []))}")
        print(f"Strengths: {len(analysis.get('strengths', []))} found")
        print(f"Red Flags: {len(analysis.get('red_flags', []))} found")
        print(f"{'═' * 50}")
        print("\n✅ Pipeline works! You're ready for the hackathon.\n")

    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        print("   Check your API keys and network connection.\n")
        raise


if __name__ == "__main__":
    asyncio.run(main())
