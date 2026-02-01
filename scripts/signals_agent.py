#!/usr/bin/env python3
"""
Signals AI Agent

An intelligent agent that can interact with the Signals API to analyze companies,
search for intelligence, and retrieve market insights.

Usage:
    python scripts/signals_agent.py analyze Anthropic
    python scripts/signals_agent.py search "AI company"
    python scripts/signals_agent.py company anthropic
    python scripts/signals_agent.py highlights anthropic
    python scripts/signals_agent.py chat "What is Anthropic?"
    python scripts/signals_agent.py vector-scores anthropic
"""
import argparse
import json
import os
import sys
import time
from typing import Any, Dict, Optional

try:
    import httpx
except ImportError:
    print("Error: httpx not installed. Run: pip install httpx")
    sys.exit(1)

# Default configuration
DEFAULT_BASE_URL = os.getenv("SIGNALS_API_URL", "http://localhost:3001")


class SignalsAgent:
    """AI Agent for interacting with Signals API."""
    
    def __init__(self, base_url: str = DEFAULT_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=30.0)
    
    def health_check(self) -> bool:
        """Check if API is available."""
        try:
            response = self.client.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def analyze_company(self, company_name: str) -> Dict[str, Any]:
        """
        Run full pipeline analysis on a company.
        
        Args:
            company_name: Name of the company to analyze
            
        Returns:
            Analysis results with company data
        """
        print(f"🔍 Analyzing {company_name}...")
        print("This may take 30-60 seconds...\n")
        
        try:
            response = self.client.post(
                f"{self.base_url}/api/analyze",
                json={"name": company_name},
                timeout=120
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("success"):
                print(f"✅ Analysis complete!")
                company_data = data.get("data", {})
                print(f"   Company: {company_data.get('name', 'N/A')}")
                print(f"   Slug: {company_data.get('slug', 'N/A')}")
                return data
            else:
                print(f"❌ Analysis failed: {data.get('error', 'Unknown error')}")
                return data
                
        except httpx.TimeoutException:
            print("❌ Request timed out")
            return {"error": "Request timed out"}
        except Exception as e:
            print(f"❌ Error: {e}")
            return {"error": str(e)}
    
    def search_companies(self, query: str) -> Dict[str, Any]:
        """
        Search for companies.
        
        Args:
            query: Search query
            
        Returns:
            List of matching companies
        """
        print(f"🔍 Searching for: {query}")
        
        try:
            response = self.client.get(
                f"{self.base_url}/api/companies/search",
                params={"q": query},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            companies = data.get("companies", [])
            print(f"✅ Found {len(companies)} companies\n")
            
            for i, company in enumerate(companies[:5], 1):
                print(f"  {i}. {company.get('name', 'N/A')}")
                print(f"     Sector: {company.get('sector', 'N/A')}")
                print(f"     Website: {company.get('website', 'N/A')}")
                print()
            
            return data
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return {"error": str(e)}
    
    def get_company(self, slug: str) -> Dict[str, Any]:
        """
        Get full company details.
        
        Args:
            slug: Company slug
            
        Returns:
            Company profile
        """
        print(f"📊 Fetching company: {slug}")
        
        try:
            response = self.client.get(
                f"{self.base_url}/api/company/{slug}",
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if "error" not in data:
                print(f"✅ Retrieved company details\n")
                print(f"   Name: {data.get('name', 'N/A')}")
                print(f"   Sector: {data.get('sector', 'N/A')}")
                print(f"   Website: {data.get('website', 'N/A')}")
                print(f"   Description: {data.get('description', 'N/A')[:100]}...")
            else:
                print(f"❌ {data.get('error', 'Not found')}")
            
            return data
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return {"error": str(e)}
    
    def get_highlights(self, slug: Optional[str] = None) -> Dict[str, Any]:
        """
        Get company highlights or all highlights.
        
        Args:
            slug: Optional company slug. If None, returns all highlights
            
        Returns:
            Highlights data
        """
        if slug:
            print(f"📈 Fetching highlights for: {slug}")
            url = f"{self.base_url}/api/company/{slug}/highlights"
        else:
            print("📈 Fetching all highlights")
            url = f"{self.base_url}/api/highlights"
        
        try:
            response = self.client.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if "error" not in data:
                if slug:
                    signals = data.get("signals", {})
                    print(f"✅ Highlights retrieved\n")
                    print(f"   Signal Score: {signals.get('score', 'N/A')}")
                    print(f"   Positive Signals: {len(signals.get('positive', []))}")
                    print(f"   Negative Signals: {len(signals.get('negative', []))}")
                else:
                    highlights = data.get("highlights", [])
                    print(f"✅ Retrieved {len(highlights)} company highlights\n")
                    for h in highlights[:3]:
                        name = h.get("company", {}).get("name", "Unknown")
                        score = h.get("signals", {}).get("score", "N/A")
                        print(f"   {name}: Score {score}")
            else:
                print(f"❌ {data.get('error', 'Not found')}")
            
            return data
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return {"error": str(e)}
    
    def chat(self, message: str) -> str:
        """
        Chat with the RAG system.
        
        Args:
            message: User message/question
            
        Returns:
            Response text
        """
        print(f"💬 Chatting: {message}\n")
        
        try:
            response = self.client.post(
                f"{self.base_url}/api/chat",
                json={"message": message},
                timeout=30
            )
            
            if response.status_code == 200:
                # For SSE streaming, we'd need to handle it differently
                # For now, just show that it's working
                print("✅ Chat endpoint responding")
                print("   (Full streaming requires SSE client)")
                return "Chat endpoint is active"
            else:
                error = response.text[:200]
                print(f"❌ Chat failed: {error}")
                return error
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return str(e)
    
    def get_vector_scores(self, slug: str) -> Dict[str, Any]:
        """
        Get AI-calculated vector scores for a company.
        
        Args:
            slug: Company slug
            
        Returns:
            Vector scores data
        """
        print(f"📊 Calculating vector scores for: {slug}")
        print("This may take 10-20 seconds...\n")
        
        try:
            response = self.client.get(
                f"{self.base_url}/api/companies/{slug}/vector-scores",
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("success"):
                print("✅ Vector scores calculated\n")
                
                if "crossVectorData" in data:
                    vectors = data["crossVectorData"].get("vectors", [])
                    values = data["crossVectorData"].get("values", [])
                    
                    print("Vector Scores:")
                    for vec, val in zip(vectors, values):
                        print(f"   {vec['label']}: {val:.2f}")
                
                if "signals" in data:
                    print("\nSignal Status:")
                    for signal in data["signals"]:
                        print(f"   {signal['type']}: {signal['status']}")
            
            return data
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return {"error": str(e)}
    
    def list_companies(self, watchlist_only: bool = False) -> Dict[str, Any]:
        """
        List all companies.
        
        Args:
            watchlist_only: Only show watchlisted companies
            
        Returns:
            List of companies
        """
        print("📋 Listing companies...")
        
        try:
            params = {"watchlist": "true"} if watchlist_only else {}
            response = self.client.get(
                f"{self.base_url}/api/companies",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            companies = data.get("companies", [])
            print(f"✅ Found {len(companies)} companies\n")
            
            for i, company in enumerate(companies[:10], 1):
                print(f"  {i}. {company.get('name', 'N/A')} ({company.get('slug', 'N/A')})")
            
            return data
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return {"error": str(e)}


def main():
    parser = argparse.ArgumentParser(
        description="Signals AI Agent - Interact with Signals API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s analyze Anthropic
  %(prog)s search "AI company"
  %(prog)s company anthropic
  %(prog)s highlights anthropic
  %(prog)s chat "What is Anthropic?"
  %(prog)s vector-scores anthropic
  %(prog)s list
        """
    )
    
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"API base URL (default: {DEFAULT_BASE_URL})"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Run full pipeline analysis")
    analyze_parser.add_argument("company", help="Company name to analyze")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search companies")
    search_parser.add_argument("query", help="Search query")
    
    # Company command
    company_parser = subparsers.add_parser("company", help="Get company details")
    company_parser.add_argument("slug", help="Company slug")
    
    # Highlights command
    highlights_parser = subparsers.add_parser("highlights", help="Get highlights")
    highlights_parser.add_argument("slug", nargs="?", help="Company slug (optional, shows all if omitted)")
    
    # Chat command
    chat_parser = subparsers.add_parser("chat", help="Chat with RAG system")
    chat_parser.add_argument("message", help="Message/question")
    
    # Vector scores command
    vector_parser = subparsers.add_parser("vector-scores", help="Get vector scores")
    vector_parser.add_argument("slug", help="Company slug")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all companies")
    list_parser.add_argument("--watchlist", action="store_true", help="Only watchlisted companies")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Initialize agent
    agent = SignalsAgent(args.base_url)
    
    # Check health
    if not agent.health_check():
        print(f"❌ Cannot connect to API at {args.base_url}")
        print("   Make sure the server is running:")
        print("   uvicorn app.main:app --reload --port 3001")
        sys.exit(1)
    
    # Execute command
    try:
        if args.command == "analyze":
            result = agent.analyze_company(args.company)
            if result.get("success"):
                slug = result.get("data", {}).get("slug")
                if slug:
                    print(f"\n💡 Tip: Use 'company {slug}' to see full details")
        
        elif args.command == "search":
            agent.search_companies(args.query)
        
        elif args.command == "company":
            agent.get_company(args.slug)
        
        elif args.command == "highlights":
            agent.get_highlights(args.slug if args.slug else None)
        
        elif args.command == "chat":
            agent.chat(args.message)
        
        elif args.command == "vector-scores":
            agent.get_vector_scores(args.slug)
        
        elif args.command == "list":
            agent.list_companies(args.watchlist)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

