#!/usr/bin/env python3
"""
Signals API Demo Script

Tests all major endpoints for backend demo purposes.
Run with: python scripts/demo_server.py

Options:
  --base-url URL     API base URL (default: http://localhost:3001)
  --company NAME     Company to analyze (default: Anthropic)
  --skip-slow        Skip slow operations (pipeline, vector scores)
  --interactive      Interactive mode with prompts
"""
import argparse
import json
import sys
import time
from typing import Any, Dict
import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.markdown import Markdown

console = Console()

# Default configuration
DEFAULT_BASE_URL = "http://localhost:3001"
DEFAULT_COMPANY = "Anthropic"


def print_section(title: str):
    """Print a section header."""
    console.print(f"\n[bold cyan]{'='*60}[/bold cyan]")
    console.print(f"[bold cyan]{title}[/bold cyan]")
    console.print(f"[bold cyan]{'='*60}[/bold cyan]\n")


def print_response(title: str, response: httpx.Response, data: Any = None):
    """Print a formatted API response."""
    if data is None:
        try:
            data = response.json()
        except:
            data = response.text
    
    status_emoji = "✓" if response.status_code < 400 else "✗"
    status_color = "green" if response.status_code < 400 else "red"
    
    console.print(f"\n[bold]{status_emoji} {title}[/bold]")
    console.print(f"  Status: [{status_color}]{response.status_code}[/{status_color}]")
    console.print(f"  URL: {response.url}")
    
    if isinstance(data, dict):
        # Pretty print JSON
        console.print(Panel(
            json.dumps(data, indent=2, default=str),
            title="Response",
            border_style="blue"
        ))
    elif isinstance(data, list):
        console.print(f"  Items: {len(data)}")
        if data:
            console.print(Panel(
                json.dumps(data[:3], indent=2, default=str) + ("\n..." if len(data) > 3 else ""),
                title="Response (first 3)",
                border_style="blue"
            ))
    else:
        console.print(f"  Response: {data}")


def test_health(base_url: str) -> bool:
    """Test health check endpoint."""
    print_section("1. Health Check")
    
    try:
        response = httpx.get(f"{base_url}/health", timeout=5)
        print_response("Health Check", response)
        return response.status_code == 200
    except httpx.ConnectError:
        console.print("[red]✗ Cannot connect to server. Is it running?[/red]")
        console.print(f"   Try: uvicorn app.main:app --reload --port 3001")
        return False
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
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
            console.print(f"\n[green]✓ Found {count} companies[/green]")
            
            # Show first company summary
            if count > 0:
                first = data["companies"][0]
                console.print(f"\n[bold]First Company:[/bold]")
                console.print(f"  Name: {first.get('name', 'N/A')}")
                console.print(f"  Sector: {first.get('sector', 'N/A')}")
                console.print(f"  Website: {first.get('website', 'N/A')}")
        else:
            console.print("[yellow]⚠ No companies found. Run /analyze first.[/yellow]")
            
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")


def test_search_companies(base_url: str, query: str = "AI"):
    """Test company search."""
    print_section("3. Search Companies")
    
    try:
        response = httpx.get(f"{base_url}/api/companies/search", params={"q": query}, timeout=10)
        data = response.json()
        print_response(f"Search Companies (query: '{query}')", response, data)
        
        if data.get("companies"):
            console.print(f"\n[green]✓ Found {len(data['companies'])} results[/green]")
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")


def test_analyze_company(base_url: str, company_name: str, skip_slow: bool = False):
    """Test company analysis pipeline."""
    print_section("4. Analyze Company (Pipeline)")
    
    if skip_slow:
        console.print("[yellow]⚠ Skipping slow pipeline test (use --no-skip-slow to run)[/yellow]")
        return None
    
    try:
        console.print(f"[bold]Analyzing: {company_name}[/bold]")
        console.print("[yellow]This may take 30-60 seconds...[/yellow]\n")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Running pipeline...", total=None)
            
            response = httpx.post(
                f"{base_url}/api/analyze",
                json={"name": company_name},
                timeout=120
            )
            
            progress.update(task, completed=True)
        
        data = response.json()
        print_response(f"Analyze Company: {company_name}", response, data)
        
        if data.get("success"):
            console.print(f"\n[green]✓ Pipeline completed successfully![/green]")
            if "data" in data:
                company_data = data["data"]
                console.print(f"  Company: {company_data.get('name', 'N/A')}")
                console.print(f"  Slug: {company_data.get('slug', 'N/A')}")
        else:
            console.print(f"[red]✗ Pipeline failed: {data.get('error', 'Unknown error')}[/red]")
        
        return data.get("data", {}).get("slug") if data.get("success") else None
        
    except httpx.TimeoutException:
        console.print("[red]✗ Request timed out. Pipeline may be taking longer than expected.[/red]")
        return None
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        return None


def test_company_details(base_url: str, slug: str):
    """Test getting company details."""
    print_section("5. Company Details")
    
    try:
        response = httpx.get(f"{base_url}/api/company/{slug}", timeout=10)
        data = response.json()
        print_response(f"Get Company: {slug}", response, data)
        
        if "error" not in data:
            console.print(f"\n[green]✓ Retrieved company details[/green]")
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")


def test_company_highlights(base_url: str, slug: str):
    """Test company highlights."""
    print_section("6. Company Highlights")
    
    try:
        response = httpx.get(f"{base_url}/api/company/{slug}/highlights", timeout=10)
        data = response.json()
        print_response(f"Get Highlights: {slug}", response, data)
        
        if "error" not in data:
            console.print(f"\n[green]✓ Retrieved highlights[/green]")
            if "signals" in data:
                signals = data["signals"]
                console.print(f"  Signal Score: {signals.get('score', 'N/A')}")
                console.print(f"  Positive Signals: {len(signals.get('positive', []))}")
                console.print(f"  Negative Signals: {len(signals.get('negative', []))}")
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")


def test_all_highlights(base_url: str):
    """Test getting all highlights."""
    print_section("7. All Highlights")
    
    try:
        response = httpx.get(f"{base_url}/api/highlights", params={"limit": 5}, timeout=10)
        data = response.json()
        print_response("Get All Highlights", response, data)
        
        if "highlights" in data:
            count = len(data["highlights"])
            console.print(f"\n[green]✓ Retrieved {count} company highlights[/green]")
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")


def test_vector_scores(base_url: str, slug: str, skip_slow: bool = False):
    """Test vector scores calculation."""
    print_section("8. Vector Scores")
    
    if skip_slow:
        console.print("[yellow]⚠ Skipping slow vector scores test (use --no-skip-slow to run)[/yellow]")
        return
    
    try:
        console.print("[yellow]Calculating vector scores (may take 10-20 seconds)...[/yellow]\n")
        
        response = httpx.get(f"{base_url}/api/companies/{slug}/vector-scores", timeout=30)
        data = response.json()
        print_response(f"Vector Scores: {slug}", response, data)
        
        if data.get("success"):
            console.print(f"\n[green]✓ Vector scores calculated[/green]")
            if "crossVectorData" in data:
                vectors = data["crossVectorData"].get("vectors", [])
                values = data["crossVectorData"].get("values", [])
                console.print(f"\n[bold]Vector Scores:[/bold]")
                for vec, val in zip(vectors, values):
                    console.print(f"  {vec['label']}: {val:.2f}")
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")


def test_chat(base_url: str, message: str = "What is Anthropic?"):
    """Test chat endpoint."""
    print_section("9. Chat (Streaming)")
    
    try:
        console.print(f"[bold]Question:[/bold] {message}")
        console.print("[yellow]Streaming response...[/yellow]\n")
        
        response = httpx.post(
            f"{base_url}/api/chat",
            json={"message": message},
            timeout=30
        )
        
        # For SSE, we'd need to handle streaming differently
        # For demo, just show status
        console.print(f"  Status: {response.status_code}")
        console.print(f"  Content-Type: {response.headers.get('content-type', 'N/A')}")
        
        if response.status_code == 200:
            console.print("[green]✓ Chat endpoint responding[/green]")
            console.print("[yellow]Note: Full streaming requires SSE client[/yellow]")
        else:
            console.print(f"[red]✗ Chat failed: {response.text[:200]}[/red]")
            
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")


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
            console.print(f"\n[green]✓ Found {len(discussions)} HN discussions[/green]")
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")


def test_search_job_flow(base_url: str, query: str, skip_slow: bool = False):
    """Test the search job flow (create -> poll -> results)."""
    print_section("11. Search Job Flow")
    
    if skip_slow:
        console.print("[yellow]⚠ Skipping slow job flow test (use --no-skip-slow to run)[/yellow]")
        return
    
    try:
        # Create job
        console.print(f"[bold]Creating search job for: {query}[/bold]")
        response = httpx.post(
            f"{base_url}/api/search",
            json={"query": query},
            timeout=10
        )
        job_data = response.json()
        
        if "jobId" not in job_data:
            console.print(f"[red]✗ Failed to create job: {job_data}[/red]")
            return
        
        job_id = job_data["jobId"]
        console.print(f"[green]✓ Job created: {job_id}[/green]")
        
        # Poll for status
        console.print("\n[yellow]Polling job status...[/yellow]")
        max_polls = 30
        poll_interval = 2
        
        for i in range(max_polls):
            time.sleep(poll_interval)
            
            status_response = httpx.get(f"{base_url}/api/job/{job_id}/status", timeout=5)
            status_data = status_response.json()
            
            status = status_data.get("status", "unknown")
            progress = status_data.get("progress", 0)
            
            console.print(f"  Poll {i+1}: {status} ({progress}%)")
            
            if status_data.get("isComplete"):
                if status == "completed":
                    # Get results
                    results_response = httpx.get(f"{base_url}/api/job/{job_id}/results", timeout=10)
                    results_data = results_response.json()
                    console.print(f"\n[green]✓ Job completed![/green]")
                    print_response("Job Results", results_response, results_data)
                else:
                    console.print(f"\n[red]✗ Job failed: {status_data.get('error', 'Unknown error')}[/red]")
                break
        
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")


def run_demo(base_url: str, company_name: str, skip_slow: bool = False, interactive: bool = False):
    """Run the full demo."""
    console.print("\n[bold green]Signals API Demo[/bold green]")
    console.print(f"Base URL: {base_url}\n")
    
    # Test 1: Health check (required)
    if not test_health(base_url):
        console.print("\n[red]Server is not running. Please start it first:[/red]")
        console.print("[yellow]  uvicorn app.main:app --reload --port 3001[/yellow]\n")
        return
    
    # Test 2: List companies
    test_list_companies(base_url)
    
    # Test 3: Search companies
    test_search_companies(base_url, "AI")
    
    # Test 4: Analyze company (creates data)
    slug = None
    if interactive:
        response = console.input("\n[bold]Run pipeline analysis? (y/n): [/bold]")
        if response.lower() == 'y':
            slug = test_analyze_company(base_url, company_name, skip_slow=False)
    else:
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
                    console.print(f"\n[yellow]Using existing company: {slug}[/yellow]")
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
    if interactive:
        response = console.input("\n[bold]Test search job flow? (y/n): [/bold]")
        if response.lower() == 'y':
            test_search_job_flow(base_url, company_name, skip_slow=False)
    else:
        test_search_job_flow(base_url, company_name, skip_slow)
    
    # Summary
    print_section("Demo Complete")
    console.print("[green]✓ All tests completed![/green]")
    console.print(f"\n[bold]API Base URL:[/bold] {base_url}")
    console.print(f"[bold]Test Company:[/bold] {company_name}")


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
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactive mode with prompts"
    )
    
    args = parser.parse_args()
    
    try:
        run_demo(args.base_url, args.company, args.skip_slow, args.interactive)
    except KeyboardInterrupt:
        console.print("\n[yellow]Demo interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Demo failed: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

