"""
Fix the knowledge collection by recreating it as a standard collection.

Time Series collections don't support Vector Search indexes, so we need
to recreate knowledge as a standard collection.

Usage:
    python scripts/fix_knowledge_collection.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymongo import MongoClient, ASCENDING
from app.config import settings


def fix_knowledge_collection():
    print("=" * 60)
    print("Fixing knowledge collection")
    print("=" * 60)

    # Connect
    client = MongoClient(settings.mongodb_uri)
    try:
        db = client.get_default_database()
    except Exception:
        db = client["signals"]

    print(f"\nConnected to database: {db.name}")

    # Check current collection info
    collections = db.list_collection_names()
    print(f"Existing collections: {collections}")

    if "knowledge" in collections:
        # Get collection info
        coll_info = db.command({"listCollections": 1, "filter": {"name": "knowledge"}})
        coll_details = list(coll_info.get("cursor", {}).get("firstBatch", []))

        if coll_details:
            coll_type = coll_details[0].get("type", "collection")
            options = coll_details[0].get("options", {})
            print(f"\nCurrent 'knowledge' collection:")
            print(f"  Type: {coll_type}")
            print(f"  Options: {options}")

            if "timeseries" in options:
                print("\n  ⚠️  This is a Time Series collection!")
                print("  Time Series collections don't support Vector Search.")

        # Count existing documents
        doc_count = db.knowledge.count_documents({})
        print(f"\n  Documents: {doc_count}")

        if doc_count > 0:
            print("\n  Backing up existing data...")
            existing_docs = list(db.knowledge.find({}))
            # Remove _id fields for re-insertion
            for doc in existing_docs:
                doc.pop("_id", None)
            print(f"  Backed up {len(existing_docs)} documents")
        else:
            existing_docs = []

        # Drop the collection
        print("\n  Dropping time series collection...")
        db.drop_collection("knowledge")
        print("  Dropped!")

        # Recreate as standard collection
        print("\n  Creating standard collection...")
        db.create_collection("knowledge")

        # Create indexes
        db.knowledge.create_index("company_slug", name="company_slug_idx")
        db.knowledge.create_index(
            [("company_slug", ASCENDING), ("source", ASCENDING)],
            name="slug_source_idx"
        )
        print("  Created indexes: company_slug_idx, slug_source_idx")

        # Restore data if any
        if existing_docs:
            print(f"\n  Restoring {len(existing_docs)} documents...")
            db.knowledge.insert_many(existing_docs)
            print("  Restored!")

        print("\n  ✅ knowledge collection recreated as standard collection!")

    else:
        print("\n  'knowledge' collection doesn't exist. Creating...")
        db.create_collection("knowledge")
        db.knowledge.create_index("company_slug", name="company_slug_idx")
        db.knowledge.create_index(
            [("company_slug", ASCENDING), ("source", ASCENDING)],
            name="slug_source_idx"
        )
        print("  ✅ Created standard collection with indexes!")

    # Verify
    print("\n" + "=" * 60)
    print("Verification")
    print("=" * 60)

    coll_info = db.command({"listCollections": 1, "filter": {"name": "knowledge"}})
    coll_details = list(coll_info.get("cursor", {}).get("firstBatch", []))

    if coll_details:
        options = coll_details[0].get("options", {})
        if "timeseries" in options:
            print("❌ Still a time series collection!")
        else:
            print("✅ knowledge is now a standard collection")
            print("\nNext step: Create the vector_index in Atlas UI:")
            print("  1. Go to Atlas → Browse Collections → signals.knowledge")
            print("  2. Click 'Search Indexes' tab → 'Create Search Index'")
            print("  3. Select 'Atlas Vector Search' → JSON Editor")
            print("  4. Index name: vector_index")
            print("  5. Paste this definition:")
            print("""
{
  "fields": [
    {
      "type": "vector",
      "path": "vector",
      "numDimensions": 384,
      "similarity": "cosine"
    },
    {
      "type": "filter",
      "path": "company_slug"
    }
  ]
}
""")

    doc_count = db.knowledge.count_documents({})
    print(f"\nDocuments in knowledge: {doc_count}")

    client.close()


if __name__ == "__main__":
    fix_knowledge_collection()
