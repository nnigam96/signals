import asyncio
import json
import os
import sys
import time
from typing import Dict, Any, List
from dotenv import load_dotenv

# Fix path to import from app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from app.pipeline.mongodb import connect_db, get_knowledge_collection, make_slug
from app.pipeline.firecrawl import crawl_company
from app.pipeline.rag import process_and_store_knowledge, chunk_text
from app.pipeline.mongodb import search_knowledge

async def test_firecrawl_rag_integration(company_name: str) -> Dict[str, Any]:
    """
    Integration test: Company name → Firecrawl → RAG → Metrics
    
    Flow:
    1. Take company name
    2. Run Firecrawl to gather data
    3. Store in RAG (chunk + embed)
    4. Query RAG for insights
    5. Return metrics
    """
    print(f"\n{'='*60}")
    print(f"FIRECRAWL + RAG INTEGRATION TEST")
    print(f"{'='*60}")
    print(f"Company: {company_name}")
    print(f"{'='*60}\n")
    
    metrics = {
        "company_name": company_name,
        "timings": {},
        "firecrawl": {},
        "rag": {},
        "queries": []
    }
    
    # Step 1: Connect to DB
    print("[1/5] Connecting to MongoDB...")
    connect_db()
    start_time = time.time()
    metrics["timings"]["db_connect"] = time.time() - start_time
    print("✓ Connected\n")
    
    # Step 2: Firecrawl - Gather data
    print(f"[2/5] Running Firecrawl for '{company_name}'...")
    crawl_start = time.time()
    
    try:
        crawl_data = await crawl_company(company_name)
        crawl_time = time.time() - crawl_start
        metrics["timings"]["firecrawl"] = crawl_time
        
        metrics["firecrawl"] = {
            "url": crawl_data.get("url", ""),
            "homepage_length": len(crawl_data.get("homepage", "")),
            "news_count": len(crawl_data.get("news", [])),
            "raw_length": len(crawl_data.get("raw", "")),
            "success": True
        }
        
        print(f"✓ Firecrawl complete ({crawl_time:.2f}s)")
        print(f"  - URL: {crawl_data.get('url', 'N/A')}")
        print(f"  - Homepage: {metrics['firecrawl']['homepage_length']} chars")
        print(f"  - News snippets: {metrics['firecrawl']['news_count']}")
        print(f"  - Total raw data: {metrics['firecrawl']['raw_length']} chars\n")
        
    except Exception as e:
        metrics["firecrawl"]["success"] = False
        metrics["firecrawl"]["error"] = str(e)
        print(f"✗ Firecrawl failed: {e}\n")
        return metrics
    
    # Step 3: Store in RAG
    print(f"[3/5] Storing data in RAG...")
    rag_start = time.time()
    
    slug = make_slug(company_name)
    raw_text = crawl_data.get("raw", "")
    
    if not raw_text:
        print("✗ No data to store in RAG\n")
        metrics["rag"]["success"] = False
        metrics["rag"]["error"] = "No raw text from Firecrawl"
        return metrics
    
    # Chunk the text
    chunks = chunk_text(raw_text)
    metrics["rag"]["chunks_created"] = len(chunks)
    metrics["rag"]["avg_chunk_size"] = sum(len(c) for c in chunks) / len(chunks) if chunks else 0
    
    # Store in RAG
    try:
        await process_and_store_knowledge(slug, raw_text, "web")
        rag_time = time.time() - rag_start
        metrics["timings"]["rag_store"] = rag_time
        
        # Verify storage
        coll = get_knowledge_collection()
        stored_count = coll.count_documents({"company_slug": slug, "source": "web"})
        
        metrics["rag"]["chunks_stored"] = stored_count
        metrics["rag"]["success"] = True
        
        print(f"✓ RAG storage complete ({rag_time:.2f}s)")
        print(f"  - Chunks created: {metrics['rag']['chunks_created']}")
        print(f"  - Chunks stored: {metrics['rag']['chunks_stored']}")
        print(f"  - Avg chunk size: {metrics['rag']['avg_chunk_size']:.0f} chars\n")
        
    except Exception as e:
        metrics["rag"]["success"] = False
        metrics["rag"]["error"] = str(e)
        print(f"✗ RAG storage failed: {e}\n")
        return metrics
    
    # Step 4: Query RAG for insights
    print(f"[4/5] Querying RAG for insights...")
    query_start = time.time()
    
    test_queries = [
        f"What is {company_name}?",
        f"What does {company_name} do?",
        f"What are {company_name}'s main products or services?",
        f"Tell me about {company_name}'s business model",
        f"What is {company_name}'s market position?",
    ]
    
    query_results = []
    for query in test_queries:
        try:
            results = search_knowledge(query, company_slug=slug, limit=3)
            
            query_metrics = {
                "query": query,
                "results_count": len(results),
                "top_score": results[0].get("score", 0) if results else 0,
                "sources": list(set(r.get("source", "unknown") for r in results)),
                "success": True
            }
            
            if results:
                query_metrics["top_result_preview"] = results[0].get("text", "")[:150]
            
            query_results.append(query_metrics)
            metrics["queries"].append(query_metrics)
            
        except Exception as e:
            query_metrics = {
                "query": query,
                "success": False,
                "error": str(e)
            }
            query_results.append(query_metrics)
            metrics["queries"].append(query_metrics)
    
    query_time = time.time() - query_start
    metrics["timings"]["rag_queries"] = query_time
    
    successful_queries = sum(1 for q in query_results if q.get("success", False))
    print(f"✓ Queried RAG ({query_time:.2f}s)")
    print(f"  - Queries executed: {len(test_queries)}")
    print(f"  - Successful: {successful_queries}")
    print(f"  - Failed: {len(test_queries) - successful_queries}\n")
    
    # Step 5: Display metrics and insights
    print(f"[5/5] Metrics Summary")
    print(f"{'='*60}\n")
    
    # Timing metrics
    total_time = sum(metrics["timings"].values())
    print("TIMING METRICS:")
    for key, value in metrics["timings"].items():
        print(f"  {key.replace('_', ' ').title()}: {value:.2f}s")
    print(f"  Total: {total_time:.2f}s\n")
    
    # RAG metrics
    print("RAG METRICS:")
    print(f"  Chunks Created: {metrics['rag'].get('chunks_created', 0)}")
    print(f"  Chunks Stored: {metrics['rag'].get('chunks_stored', 0)}")
    print(f"  Avg Chunk Size: {metrics['rag'].get('avg_chunk_size', 0):.0f} chars")
    print(f"  Storage Time: {metrics['timings'].get('rag_store', 0):.2f}s\n")
    
    # Query metrics
    print("QUERY METRICS:")
    avg_results = sum(q.get("results_count", 0) for q in query_results) / len(query_results) if query_results else 0
    avg_score = sum(q.get("top_score", 0) for q in query_results if q.get("success")) / successful_queries if successful_queries > 0 else 0
    print(f"  Avg Results per Query: {avg_results:.1f}")
    print(f"  Avg Top Score: {avg_score:.4f}")
    print(f"  Query Success Rate: {successful_queries}/{len(test_queries)} ({100*successful_queries/len(test_queries):.0f}%)\n")
    
    # Sample insights
    print("SAMPLE INSIGHTS:")
    for i, query_result in enumerate(query_results[:3], 1):
        if query_result.get("success") and query_result.get("results_count", 0) > 0:
            print(f"\n  Query {i}: {query_result['query']}")
            print(f"    Results: {query_result['results_count']}, Score: {query_result['top_score']:.4f}")
            if "top_result_preview" in query_result:
                print(f"    Preview: {query_result['top_result_preview']}...")
    
    # Save full metrics to file
    output_file = f"firecrawl_rag_metrics_{slug}.json"
    with open(output_file, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"\n✓ Full metrics saved to: {output_file}")
    
    return metrics

async def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_firecrawl_rag_integration.py <company_name>")
        print("Example: python scripts/test_firecrawl_rag_integration.py Anthropic")
        sys.exit(1)
    
    company_name = " ".join(sys.argv[1:])
    
    try:
        metrics = await test_firecrawl_rag_integration(company_name)
        
        # Exit code based on success
        if metrics.get("firecrawl", {}).get("success") and metrics.get("rag", {}).get("success"):
            print(f"\n{'='*60}")
            print("✓ INTEGRATION TEST PASSED")
            print(f"{'='*60}\n")
            sys.exit(0)
        else:
            print(f"\n{'='*60}")
            print("✗ INTEGRATION TEST FAILED")
            print(f"{'='*60}\n")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

