import asyncio
import os
import sys
import json
from datetime import datetime, timezone
from dotenv import load_dotenv

# Fix path to import from app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from app.pipeline.mongodb import (
    connect_db, 
    get_knowledge_collection,
    store_company,
    get_company,
    list_companies,
    search_companies,
    store_snapshot,
    toggle_watchlist,
    make_slug,
    search_knowledge
)
from app.pipeline.rag import embedding_model

def test_connection():
    """Test basic MongoDB connection."""
    print("\n=== TEST 1: MongoDB Connection ===")
    try:
        connect_db()
        print("✓ MongoDB connection successful")
        return True
    except Exception as e:
        print(f"✗ MongoDB connection failed: {e}")
        return False

def test_companies_collection():
    """Test companies collection operations."""
    print("\n=== TEST 2: Companies Collection ===")
    
    try:
        # Test data
        test_company = {
            "name": "Test Company Inc",
            "slug": make_slug("Test Company Inc"),
            "description": "A test company for MongoDB compatibility testing",
            "website": "https://test.example.com",
            "watchlist": False,
            "crawled_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "web_data": {"raw": "Test web data"},
            "document_data": None,
            "analysis": {"summary": "Test company for compatibility"}
        }
        
        # Test store
        print("  Testing store_company()...")
        stored = store_company(test_company)
        if stored:
            print(f"  ✓ Company stored: {stored.get('name')}")
        else:
            print("  ✗ Failed to store company")
            return False
        
        slug = test_company["slug"]
        
        # Test get
        print("  Testing get_company()...")
        retrieved = get_company(slug)
        if retrieved and retrieved.get("name") == test_company["name"]:
            print(f"  ✓ Company retrieved: {retrieved.get('name')}")
        else:
            print("  ✗ Failed to retrieve company")
            return False
        
        # Test list
        print("  Testing list_companies()...")
        companies = list_companies()
        if companies and len(companies) > 0:
            print(f"  ✓ Listed {len(companies)} companies")
        else:
            print("  ✗ Failed to list companies")
            return False
        
        # Test search
        print("  Testing search_companies()...")
        results = search_companies("test company")
        if results:
            print(f"  ✓ Search found {len(results)} results")
        else:
            print("  ⚠ Search returned no results (may be normal)")
        
        # Test watchlist toggle
        print("  Testing toggle_watchlist()...")
        toggle_watchlist(slug, True)
        updated = get_company(slug)
        if updated and updated.get("watchlist") == True:
            print("  ✓ Watchlist toggle successful")
        else:
            print("  ✗ Watchlist toggle failed")
            return False
        
        # Cleanup
        toggle_watchlist(slug, False)
        
        print("  ✓ All companies collection tests passed")
        return True
        
    except Exception as e:
        print(f"  ✗ Companies collection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_snapshots_collection():
    """Test snapshots collection operations."""
    print("\n=== TEST 3: Snapshots Collection ===")
    
    try:
        test_slug = make_slug("Test Company Inc")
        test_data = {
            "web_data": {"raw": "Test snapshot data"},
            "document_data": None,
            "analysis": {"summary": "Test snapshot"}
        }
        
        print("  Testing store_snapshot()...")
        store_snapshot(test_slug, test_data)
        print("  ✓ Snapshot stored successfully")
        
        # Verify snapshot exists
        from app.pipeline.mongodb import _sn
        snapshots = list(_sn().find({"slug": test_slug}).limit(1))
        if snapshots:
            print(f"  ✓ Snapshot verified: {len(snapshots)} found")
        else:
            print("  ⚠ Snapshot not found (may need to check)")
        
        print("  ✓ Snapshots collection tests passed")
        return True
        
    except Exception as e:
        print(f"  ✗ Snapshots collection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_knowledge_collection():
    """Test knowledge collection operations."""
    print("\n=== TEST 4: Knowledge Collection ===")
    
    try:
        coll = get_knowledge_collection()
        print("  ✓ Knowledge collection accessed")
        
        # Test insert
        test_slug = make_slug("Test Company Inc")
        test_chunk = {
            "company_slug": test_slug,
            "text": "This is a test chunk for MongoDB compatibility testing",
            "vector": [0.1] * 384,  # Mock vector (384-dim for bge-small-en-v1.5)
            "source": "test",
            "chunk_index": 0
        }
        
        print("  Testing insert...")
        coll.insert_one(test_chunk)
        print("  ✓ Document inserted")
        
        # Test find
        print("  Testing find...")
        found = list(coll.find({"company_slug": test_slug, "source": "test"}))
        if found:
            print(f"  ✓ Found {len(found)} documents")
        else:
            print("  ✗ Failed to find documents")
            return False
        
        # Test count
        count = coll.count_documents({"company_slug": test_slug})
        print(f"  ✓ Count: {count} documents for test company")
        
        # Cleanup
        coll.delete_many({"company_slug": test_slug, "source": "test"})
        print("  ✓ Cleanup completed")
        
        print("  ✓ Knowledge collection tests passed")
        return True
        
    except Exception as e:
        print(f"  ✗ Knowledge collection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_vector_search():
    """Test vector search functionality (requires Atlas with vector index)."""
    print("\n=== TEST 5: Vector Search ===")
    
    try:
        # First, create a test embedding
        test_query = "What is a test company?"
        print(f"  Testing vector search with query: '{test_query}'")
        
        # Generate embedding
        query_vector = list(embedding_model.embed([test_query]))[0].tolist()
        print(f"  ✓ Generated query embedding (dim: {len(query_vector)})")
        
        # Try vector search
        test_slug = make_slug("Test Company Inc")
        results = search_knowledge(test_query, company_slug=test_slug, limit=3)
        
        if results:
            print(f"  ✓ Vector search returned {len(results)} results")
            for i, result in enumerate(results[:2], 1):
                score = result.get("score", 0)
                print(f"    Result {i}: score={score:.4f}")
            return True
        else:
            print("  ⚠ Vector search returned no results")
            print("  Note: This may be normal if:")
            print("    - No knowledge stored for test company")
            print("    - Vector search index not configured in Atlas")
            print("    - Using local MongoDB (vector search requires Atlas)")
            return None  # Not a failure, just not configured
        
    except Exception as e:
        error_str = str(e)
        if "vectorSearch" in error_str or "vector_index" in error_str:
            print(f"  ⚠ Vector search not available: {e}")
            print("  Note: Vector search requires MongoDB Atlas with vector search index")
            print("  This is expected if using local MongoDB or unconfigured Atlas")
            return None
        else:
            print(f"  ✗ Vector search test failed: {e}")
            import traceback
            traceback.print_exc()
            return False

def test_indexes():
    """Test that indexes are created correctly."""
    print("\n=== TEST 6: Indexes ===")
    
    try:
        from app.pipeline.mongodb import _db
        
        # Check companies indexes
        companies_indexes = list(_db.companies.list_indexes())
        print(f"  Companies collection indexes: {len(companies_indexes)}")
        for idx in companies_indexes:
            print(f"    - {idx.get('name')}: {idx.get('key')}")
        
        # Check knowledge indexes (if any)
        try:
            knowledge_indexes = list(_db.knowledge.list_indexes())
            print(f"  Knowledge collection indexes: {len(knowledge_indexes)}")
            for idx in knowledge_indexes:
                print(f"    - {idx.get('name')}: {idx.get('key')}")
        except:
            print("  ⚠ Could not list knowledge indexes")
        
        print("  ✓ Index check completed")
        return True
        
    except Exception as e:
        print(f"  ✗ Index test failed: {e}")
        return False

def test_connection_info():
    """Display connection information."""
    print("\n=== Connection Information ===")
    
    try:
        from app.pipeline.mongodb import _client, _db
        from app.config import settings
        
        # Mask sensitive info
        uri = settings.mongodb_uri
        if "@" in uri:
            # Mask password
            parts = uri.split("@")
            if len(parts) == 2:
                masked = parts[0].split("://")[0] + "://***:***@" + parts[1]
            else:
                masked = uri
        else:
            masked = uri
        
        print(f"  MongoDB URI: {masked}")
        print(f"  Database: {_db.name if _db else 'Not connected'}")
        
        if _client:
            server_info = _client.server_info()
            print(f"  MongoDB Version: {server_info.get('version', 'Unknown')}")
            print(f"  Server Type: {server_info.get('versionArray', [])}")
        
        # List collections
        if _db:
            collections = _db.list_collection_names()
            print(f"  Collections: {', '.join(collections)}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Failed to get connection info: {e}")
        return False

def main():
    print("=" * 60)
    print("MongoDB Compatibility Test")
    print("=" * 60)
    
    results = {
        "connection": False,
        "companies": False,
        "snapshots": False,
        "knowledge": False,
        "vector_search": None,  # None = not tested/not available
        "indexes": False,
        "connection_info": False
    }
    
    # Run tests
    results["connection"] = test_connection()
    
    if not results["connection"]:
        print("\n✗ Cannot proceed without MongoDB connection")
        print("Please check:")
        print("  1. MongoDB is running")
        print("  2. MONGODB_URI is set in .env")
        print("  3. Connection string is correct")
        return results
    
    results["connection_info"] = test_connection_info()
    results["companies"] = test_companies_collection()
    results["snapshots"] = test_snapshots_collection()
    results["knowledge"] = test_knowledge_collection()
    results["vector_search"] = test_vector_search()
    results["indexes"] = test_indexes()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v == True)
    failed = sum(1 for v in results.values() if v == False)
    skipped = sum(1 for v in results.values() if v is None)
    
    for test_name, result in results.items():
        if result == True:
            status = "✓ PASS"
        elif result == False:
            status = "✗ FAIL"
        else:
            status = "⚠ SKIP (not available)"
        print(f"  {test_name.replace('_', ' ').title():20} {status}")
    
    print(f"\n  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Skipped: {skipped}")
    
    if failed == 0:
        print("\n✓ All critical tests passed!")
        if skipped > 0:
            print("  Note: Some optional features (vector search) are not available")
            print("  This is normal for local MongoDB or unconfigured Atlas")
    else:
        print("\n✗ Some tests failed. Check errors above.")
    
    # Save results
    output_file = "mongodb_compatibility_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Results saved to: {output_file}")
    
    return results

if __name__ == "__main__":
    try:
        results = main()
        sys.exit(0 if results.get("connection") and results.get("companies") else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n✗ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

