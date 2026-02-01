#!/usr/bin/env python3
"""
Simple Signals API Demo Script (no external dependencies beyond httpx)

Tests all major endpoints for backend demo purposes.
Run with: python scripts/demo_server_simple.py
"""
import argparse
import json
import sys
import time
from typing import Any

try:
    import httpx
except ImportError:
    print("Error: httpx not installed. Run: pip install httpx")
    sys.exit(1)

# Default configuration
DEFAULT_BASE_URL = "http://localhost:3001"
DEFAULT_COMPANY = "Anthropic"


def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60 + "\n")


def print_response(title: str, response: httpx.Response, data: Any = None):
    """Print a formatted API response."""
    if data is None:
        try:
            data = response.json()
        except:
            data = response.text
    
    status = "✓" if response.status_code < 400 else "✗"
    print(f"\n{status} {title}")
    print(f"  Status: {response.status_code}")
    print(f"  URL: {response.url}")
    print(f"\n  Response:")
    print(json.dumps(data, indent=2, default=str))


def test_health(base_url: str) -> bool:
    """Test health check endpoint."""
    print_section("1. Health Check")
    
    try:
        response = httpx.get(f"{base_url}/health", timeout=5)
        print_response("Health Check", response)
        return response.status_code == 200
    except httpx.ConnectError:
        print("✗ Cannot connect to server. Is it running?")
        print("   Try: uvicorn app.main:app --reload --port 3001")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_list_companies(base_url: str):
    """Test listing companies."""
    print_section("2. List Companies")
    
    try:
        response = httpx.get(f"{base_url}/api/companies", timeout=10)
        data = response.json()
        print_response("List Companies", response, data)
        
        if data.get("companies"):
            count = len(data["companies"])
            print(f"\n✓ Found {count} companies")
            
            if count > 0:
                first = data["companies"][0]
                print(f"\nFirst Company:")
                print(f"  Name: {first.get('name', 'N/A')}")
                print(f"  Sector: {first.get('sector', 'N/A')}")
                print(f"  Website: {first.get('website', 'N/A')}")
        else:
            print("⚠ No companies found. Run /analyze first.")
            
    except Exception as e:
        print(f"✗ Error: {e}")


def test_search_companies(base_url: str, query: str = "AI"):
    """Test company search."""
    print_section("3. Search Companies")
    
    try:
        response = httpx.get(f"{base_url}/api/companies/search", params={"q": query}, timeout=10)
        data = response.json()
        print_response(f"Search Companies (query: '{query}')", response, data)
        
        if data.get("companies"):
            print(f"\n✓ Found {len(data['companies'])} results")
    except Exception as e:
        print(f"✗ Error: {e}")


def test_analyze_company(base_url: str, company_name: str, skip_slow: bool = False):
    """Test company analysis pipeline."""
    print_section("4. Analyze Company (Pipeline)")
    
    if skip_slow:
        print("⚠ Skipping slow pipeline test (use --no-skip-slow to run)")
        return None
    
    try:
        print(f"Analyzing: {company_name}")
        print("This may take 30-60 seconds...\n")
        
        response = httpx.post(
            f"{base_url}/api/analyze",
            json={"name": company_name},
            timeout=120
        )
        
        data = response.json()
        print_response(f"Analyze Company: {company_name}", response, data)
        
        if data.get("success"):
            print(f"\n✓ Pipeline completed successfully!")
            if "data" in data:
                company_data = data["data"]
                print(f"  Company: {company_data.get('name', 'N/A')}")
                print(f"  Slug: {company_data.get('slug', 'N/A')}")
        else:
            print(f"✗ Pipeline failed: {data.get('error', 'Unknown error')}")
        
        return data.get("data", {}).get("slug") if data.get("success") else None
        
    except httpx.TimeoutException:
        print("✗ Request timed out. Pipeline may be taking longer than expected.")
        return None
    except Exception as e:
        print(f"✗ Error: {e}")
        return None


def test_company_details(base_url: str, slug: str):
    """Test getting company details."""
    print_section("5. Company Details")
    
    try:
        response = httpx.get(f"{base_url}/api/company/{slug}", timeout=10)
        data = response.json()
        print_response(f"Get Company: {slug}", response, data)
        
        if "error" not in data:
            print(f"\n✓ Retrieved company details")
    except Exception as e:
        print(f"✗ Error: {e}")


def test_company_highlights(base_url: str, slug: str):
    """Test company highlights."""
    print_section("6. Company Highlights")
    
    try:
        response = httpx.get(f"{base_url}/api/company/{slug}/highlights", timeout=10)
        data = response.json()
        print_response(f"Get Highlights: {slug}", response, data)
        
        if "error" not in data:
            print(f"\n✓ Retrieved highlights")
            if "signals" in data:
                signals = data["signals"]
                print(f"  Signal Score: {signals.get('score', 'N/A')}")
                print(f"  Positive Signals: {len(signals.get('positive', []))}")
                print(f"  Negative Signals: {len(signals.get('negative', []))}")
    except Exception as e:
        print(f"✗ Error: {e}")


def test_all_highlights(base_url: str):
    """Test getting all highlights."""
    print_section("7. All Highlights")
    
    try:
        response = httpx.get(f"{base_url}/api/highlights", params={"limit": 5}, timeout=10)
        data = response.json()
        print_response("Get All Highlights", response, data)
        
        if "highlights" in data:
            count = len(data["highlights"])
            print(f"\n✓ Retrieved {count} company highlights")
    except Exception as e:
        print(f"✗ Error: {e}")


def test_vector_scores(base_url: str, slug: str, skip_slow: bool = False):
    """Test vector scores calculation."""
    print_section("8. Vector Scores")
    
    if skip_slow:
        print("⚠ Skipping slow vector scores test (use --no-skip-slow to run)")
        return
    
    try:
        print("Calculating vector scores (may take 10-20 seconds)...\n")
        
        response = httpx.get(f"{base_url}/api/companies/{slug}/vector-scores", timeout=30)
        data = response.json()
        print_response(f"Vector Scores: {slug}", response, data)
        
        if data.get("success"):
            print(f"\n✓ Vector scores calculated")
            if "crossVectorData" in data:
                vectors = data["crossVectorData"].get("vectors", [])
                values = data["crossVectorData"].get("values", [])
                print(f"\nVector Scores:")
                for vec, val in zip(vectors, values):
                    print(f"  {vec['label']}: {val:.2f}")
    except Exception as e:
        print(f"✗ Error: {e}")


def test_chat(base_url: str, message: str = "What is Anthropic?"):
    """Test chat endpoint."""
    print_section("9. Chat (Streaming)")
    
    try:
        print(f"Question: {message}")
        print("Streaming response...\n")
        
        response = httpx.post(
            f"{base_url}/api/chat",
            json={"message": message},
            timeout=30
        )
        
        print(f"  Status: {response.status_code}")
        print(f"  Content-Type: {response.headers.get('content-type', 'N/A')}")
        
        if response.status_code == 200:
            print("✓ Chat endpoint responding")
            print("Note: Full streaming requires SSE client")
        else:
            print(f"✗ Chat failed: {response.text[:200]}")
            
    except Exception as e:
        print(f"✗ Error: {e}")


def test_hn_search(base_url: str, query: str = "Anthropic"):
    """Test HN search."""
    print_section("10. Hacker News Search")
    
    try:
        response = httpx.get(
            f"{base_url}/api/reports/hn/search",
            params={"q": query, "limit": 3},
            timeout=15
        )
        data = response.json()
        print_response(f"HN Search: {query}", response, data)
        
        if data.get("success"):
            discussions = data.get("discussions", [])
            print(f"\n✓ Found {len(discussions)} HN discussions")
    except Exception as e:
        print(f"✗ Error: {e}")


def test_search_job_flow(base_url: str, query: str, skip_slow: bool = False):
    """Test the search job flow (create -> poll -> results)."""
    print_section("11. Search Job Flow")
    
    if skip_slow:
        print("⚠ Skipping slow job flow test (use --no-skip-slow to run)")
        return
    
    try:
        # Create job
        print(f"Creating search job for: {query}")
        response = httpx.post(
            f"{base_url}/api/search",
            json={"query": query},
            timeout=10
        )
        job_data = response.json()
        
        if "jobId" not in job_data:
            print(f"✗ Failed to create job: {job_data}")
            return
        
        job_id = job_data["jobId"]
        print(f"✓ Job created: {job_id}")
        
        # Poll for status
        print("\nPolling job status...")
        max_polls = 30
        poll_interval = 2
        
        for i in range(max_polls):
            time.sleep(poll_interval)
            
            status_response = httpx.get(f"{base_url}/api/job/{job_id}/status", timeout=5)
            status_data = status_response.json()
            
            status = status_data.get("status", "unknown")
            progress = status_data.get("progress", 0)
            
            print(f"  Poll {i+1}: {status} ({progress}%)")
            
            if status_data.get("isComplete"):
                if status == "completed":
                    # Get results
                    results_response = httpx.get(f"{base_url}/api/job/{job_id}/results", timeout=10)
                    results_data = results_response.json()
                    print(f"\n✓ Job completed!")
                    print_response("Job Results", results_response, results_data)
                else:
                    print(f"\n✗ Job failed: {status_data.get('error', 'Unknown error')}")
                break
        
    except Exception as e:
        print(f"✗ Error: {e}")


def run_demo(base_url: str, company_name: str, skip_slow: bool = False):
    """Run the full demo."""
    print("\n" + "=" * 60)
    print("Signals API Demo")
    print("=" * 60)
    print(f"Base URL: {base_url}")
    print(f"Test Company: {company_name}\n")
    
    # Test 1: Health check (required)
    if not test_health(base_url):
        print("\nServer is not running. Please start it first:")
        print("  uvicorn app.main:app --reload --port 3001\n")
        return
    
    # Test 2: List companies
    test_list_companies(base_url)
    
    # Test 3: Search companies
    test_search_companies(base_url, "AI")
    
    # Test 4: Analyze company (creates data)
    slug = test_analyze_company(base_url, company_name, skip_slow)
    
    # If we have a company slug, test company-specific endpoints
    if slug:
        test_company_details(base_url, slug)
        test_company_highlights(base_url, slug)
        test_vector_scores(base_url, slug, skip_slow)
    else:
        # Try to get a slug from existing companies
        try:
            response = httpx.get(f"{base_url}/api/companies", timeout=10)
            data = response.json()
            companies = data.get("companies", [])
            if companies:
                slug = companies[0].get("slug") or companies[0].get("id", "").split("/")[-1]
                if slug:
                    print(f"\nUsing existing company: {slug}")
                    test_company_details(base_url, slug)
                    test_company_highlights(base_url, slug)
        except:
            pass
    
    # Test 5: All highlights
    test_all_highlights(base_url)
    
    # Test 6: Chat
    test_chat(base_url, f"What is {company_name}?")
    
    # Test 7: HN Search
    test_hn_search(base_url, company_name)
    
    # Test 8: Search job flow
    test_search_job_flow(base_url, company_name, skip_slow)
    
    # Summary
    print_section("Demo Complete")
    print("✓ All tests completed!")
    print(f"\nAPI Base URL: {base_url}")
    print(f"Test Company: {company_name}")


def main():
    parser = argparse.ArgumentParser(description="Signals API Demo Script")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"API base URL (default: {DEFAULT_BASE_URL})"
    )
    parser.add_argument(
        "--company",
        default=DEFAULT_COMPANY,
        help=f"Company to analyze (default: {DEFAULT_COMPANY})"
    )
    parser.add_argument(
        "--skip-slow",
        action="store_true",
        help="Skip slow operations (pipeline, vector scores, job flow)"
    )
    
    args = parser.parse_args()
    
    try:
        run_demo(args.base_url, args.company, args.skip_slow)
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nDemo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

