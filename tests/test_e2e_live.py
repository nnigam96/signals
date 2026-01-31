"""
End-to-end live test for the Signals pipeline.

This script runs the full pipeline against a real company
to verify all components work together.

Usage:
    python tests/test_e2e_live.py [company_name]
"""
import asyncio
import sys
import os
import logging

# Setup path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

from app.pipeline.orchestrator import run_pipeline
from app.pipeline.mongodb import connect_db, get_company, search_knowledge


async def test_live(target: str = "Linear"):
    """Run full pipeline test against a target company."""
    print("=" * 60)
    print(f"SIGNALS E2E TEST - Target: {target}")
    print("=" * 60)

    # Step 1: Connect to MongoDB
    print("\n[1/4] Connecting to MongoDB...")
    try:
        connect_db()
        print("     Connected!")
    except Exception as e:
        print(f"     FAILED: {e}")
        return False

    # Step 2: Run the full pipeline
    print(f"\n[2/4] Running pipeline for '{target}'...")
    print("     This may take 30-60 seconds (agents are crawling the web)...")
    try:
        result = await run_pipeline(name=target)
        print("     Pipeline completed!")
    except Exception as e:
        print(f"     FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Step 3: Verify data in MongoDB
    print("\n[3/4] Verifying data in MongoDB...")
    slug = result.get("slug") if result else None
    if not slug:
        print("     FAILED: No slug returned from pipeline")
        return False

    saved = get_company(slug)
    if saved:
        print(f"     Company found: {saved.get('name')}")
        print(f"     Slug: {saved.get('slug')}")
        print(f"     Summary: {saved.get('description', 'N/A')[:100]}...")

        # Check metrics
        metrics = saved.get("metrics", {})
        if metrics:
            print(f"     Sentiment: {metrics.get('sentiment', 'N/A')}")
            print(f"     Signal Strength: {metrics.get('signal_strength', 'N/A')}")

        # Check analysis
        analysis = saved.get("analysis", {})
        if analysis:
            print(f"     Competitors: {analysis.get('competitors', [])}")
            print(f"     Strengths: {analysis.get('strengths', [])[:2]}")
    else:
        print(f"     FAILED: Company '{slug}' not found in database")
        return False

    # Step 4: Test RAG (Vector Search)
    print("\n[4/4] Testing RAG (Vector Search)...")
    try:
        query = f"What does {target} do?"
        results = search_knowledge(query, company_slug=slug, limit=3)
        if results:
            print(f"     Found {len(results)} relevant chunks:")
            for i, r in enumerate(results[:2]):
                score = r.get("score", 0)
                text_preview = r.get("text", "")[:80]
                print(f"       [{i+1}] (score: {score:.3f}) {text_preview}...")
        else:
            print("     Warning: No RAG results (vector index may not be configured)")
    except Exception as e:
        print(f"     RAG test failed: {e}")
        print("     (This is expected if vector index is not set up in Atlas)")

    # Summary
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    print(f"  Company: {saved.get('name')}")
    print(f"  Slug: {slug}")
    print(f"  Summary: {saved.get('description', 'N/A')[:150]}...")

    if saved.get("analysis"):
        print("\n  Analysis:")
        analysis = saved.get("analysis", {})
        print(f"    - Sentiment: {analysis.get('metrics', {}).get('sentiment', 'N/A')}")
        print(f"    - Signal: {analysis.get('metrics', {}).get('signal_strength', 'N/A')}/100")
        print(f"    - PMF Score: {analysis.get('metrics', {}).get('pmf_score', 'N/A')}/10")

    print("\n  SUCCESS!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    # Get target from command line or use default
    target = sys.argv[1] if len(sys.argv) > 1 else "Linear"

    success = asyncio.run(test_live(target))
    sys.exit(0 if success else 1)
