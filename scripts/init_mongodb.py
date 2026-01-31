"""
Initialize MongoDB collections and indexes for Signals application.
Run this script once to set up the database schema.
"""
import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient, TEXT, IndexModel, ASCENDING, DESCENDING

# Fix path to import from app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from app.config import settings

def init_database():
    """Initialize MongoDB database with collections and indexes."""
    print("=" * 60)
    print("Initializing MongoDB Database")
    print("=" * 60)
    
    try:
        client = MongoClient(settings.mongodb_uri)
        db = client["signals"]
        print(f"Connected to database: {db.name}\n")
        
        # 1. Companies Collection
        print("[1/3] Setting up 'companies' collection...")
        companies = db["companies"]
        
        # Create indexes for companies
        companies_indexes = [
            IndexModel([("slug", ASCENDING)], unique=True, name="slug_unique"),
            IndexModel([("name", TEXT), ("description", TEXT)], name="text_search"),
            IndexModel([("watchlist", ASCENDING)], name="watchlist_idx"),
            IndexModel([("updated_at", DESCENDING)], name="updated_at_idx"),
            IndexModel([("crawled_at", DESCENDING)], name="crawled_at_idx"),
        ]
        companies.create_indexes(companies_indexes)
        print(f"  ✓ Created {len(companies_indexes)} indexes")
        print(f"  ✓ Collection ready: {companies.count_documents({})} documents\n")
        
        # 2. Snapshots Collection
        print("[2/3] Setting up 'snapshots' collection...")
        snapshots = db["snapshots"]
        
        snapshots_indexes = [
            IndexModel([("slug", ASCENDING), ("ts", DESCENDING)], name="slug_ts_idx"),
            IndexModel([("ts", DESCENDING)], name="ts_idx"),
        ]
        snapshots.create_indexes(snapshots_indexes)
        print(f"  ✓ Created {len(snapshots_indexes)} indexes")
        print(f"  ✓ Collection ready: {snapshots.count_documents({})} documents\n")
        
        # 3. Knowledge Collection (for RAG/Vector Search)
        print("[3/3] Setting up 'knowledge' collection...")
        knowledge = db["knowledge"]
        
        knowledge_indexes = [
            IndexModel([("company_slug", ASCENDING), ("source", ASCENDING)], name="slug_source_idx"),
            IndexModel([("company_slug", ASCENDING)], name="company_slug_idx"),
            IndexModel([("source", ASCENDING)], name="source_idx"),
            IndexModel([("chunk_index", ASCENDING)], name="chunk_index_idx"),
        ]
        knowledge.create_indexes(knowledge_indexes)
        print(f"  ✓ Created {len(knowledge_indexes)} indexes")
        print(f"  ✓ Collection ready: {knowledge.count_documents({})} documents")
        print("\n  ⚠ NOTE: Vector search index must be created manually in MongoDB Atlas UI")
        print("     - Index name: 'vector_index'")
        print("     - Field: 'vector'")
        print("     - Dimensions: 384 (for BAAI/bge-small-en-v1.5)")
        print("     - Filter fields: ['company_slug', 'source']\n")
        
        # Summary
        print("=" * 60)
        print("Database Initialization Complete!")
        print("=" * 60)
        print("\nCollections created:")
        print(f"  - companies: {companies.count_documents({}) documents")
        print(f"  - snapshots: {snapshots.count_documents({})} documents")
        print(f"  - knowledge: {knowledge.count_documents({})} documents")
        print("\nAll indexes created successfully!")
        print("\nNext steps:")
        print("  1. If using MongoDB Atlas, create vector search index in UI")
        print("  2. Run your application - collections will be used automatically")
        print("  3. Test with: python scripts/test_mongodb_compatibility.py")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)

