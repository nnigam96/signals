"""
MongoDB Schema Setup Script for Signals Application.

This script enforces data quality through JSON schema validation and
sets up search capabilities including Atlas Vector Search.

Run once to initialize or update the database schema:
    python scripts/setup_schema.py

Collections configured:
    - companies: Core company data with metrics validation
    - metrics_history: Time-series collection for historical metrics
    - knowledge: RAG vector store with Atlas Vector Search index
"""
import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT
from pymongo.errors import CollectionInvalid, OperationFailure

# Fix path to import from app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from app.config import settings


# =============================================================================
# Schema Definitions
# =============================================================================

COMPANIES_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["slug", "name", "metrics", "watchlist"],
        "properties": {
            "slug": {
                "bsonType": "string",
                "description": "Unique URL-safe identifier for the company"
            },
            "name": {
                "bsonType": "string",
                "description": "Company display name"
            },
            "watchlist": {
                "bsonType": "bool",
                "description": "Whether the company is on the watchlist"
            },
            "metrics": {
                "bsonType": "object",
                "required": ["signal_strength", "sentiment", "burn_rate"],
                "properties": {
                    "signal_strength": {
                        "bsonType": "int",
                        "minimum": 0,
                        "maximum": 100,
                        "description": "Overall signal strength score (0-100)"
                    },
                    "sentiment": {
                        "enum": ["positive", "neutral", "negative"],
                        "description": "Market sentiment classification"
                    },
                    "burn_rate": {
                        "enum": ["low", "medium", "high", "critical"],
                        "description": "Estimated cash burn rate category"
                    }
                }
            },
            "description": {"bsonType": "string"},
            "website": {"bsonType": "string"},
            "updated_at": {"bsonType": "date"},
            "crawled_at": {"bsonType": "date"}
        }
    }
}

KNOWLEDGE_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["company_slug", "vector", "text", "source"],
        "properties": {
            "company_slug": {
                "bsonType": "string",
                "description": "Reference to the company this knowledge belongs to"
            },
            "vector": {
                "bsonType": "array",
                "items": {"bsonType": "number"},
                "description": "Embedding vector (384 dimensions for bge-small-en-v1.5)"
            },
            "text": {
                "bsonType": "string",
                "description": "The text content that was embedded"
            },
            "source": {
                "bsonType": "string",
                "description": "Source type (e.g., 'firecrawl', 'reducto')"
            },
            "chunk_index": {"bsonType": "int"}
        }
    }
}

# Atlas Vector Search Index Definition
VECTOR_INDEX_DEFINITION = {
    "fields": [
        {
            "numDimensions": 384,
            "path": "vector",
            "similarity": "cosine",
            "type": "vector"
        },
        {
            "path": "company_slug",
            "type": "filter"
        }
    ]
}


# =============================================================================
# Setup Functions
# =============================================================================

def setup_companies_collection(db):
    """Create or update the companies collection with schema validation."""
    print("\n[1/3] Setting up 'companies' collection...")

    collection_name = "companies"

    # Check if collection exists
    if collection_name in db.list_collection_names():
        # Update existing collection with schema validation
        try:
            db.command({
                "collMod": collection_name,
                "validator": COMPANIES_SCHEMA,
                "validationLevel": "moderate",  # Allow existing docs that don't match
                "validationAction": "warn"      # Warn but don't reject on validation failure
            })
            print("  - Updated schema validation (moderate level)")
        except OperationFailure as e:
            print(f"  - Warning: Could not update validation: {e}")
    else:
        # Create new collection with validation
        try:
            db.create_collection(
                collection_name,
                validator=COMPANIES_SCHEMA,
                validationLevel="moderate",
                validationAction="warn"
            )
            print("  - Created collection with schema validation")
        except CollectionInvalid as e:
            print(f"  - Warning: {e}")

    companies = db[collection_name]

    # Create indexes
    companies.create_index([("slug", ASCENDING)], unique=True, name="slug_unique")
    companies.create_index([("name", TEXT), ("description", TEXT)], name="text_search")
    companies.create_index([("watchlist", ASCENDING)], name="watchlist_idx")
    companies.create_index([("updated_at", DESCENDING)], name="updated_at_idx")

    print("  - Created indexes: slug_unique, text_search, watchlist_idx, updated_at_idx")
    print(f"  - Documents: {companies.count_documents({})}")


def setup_metrics_history_collection(db):
    """Create the metrics_history time-series collection."""
    print("\n[2/3] Setting up 'metrics_history' time-series collection...")

    collection_name = "metrics_history"

    # Check if collection exists
    if collection_name in db.list_collection_names():
        # Check if it's already a time-series collection
        coll_info = db.command({"listCollections": 1, "filter": {"name": collection_name}})
        collections = list(coll_info.get("cursor", {}).get("firstBatch", []))

        if collections and collections[0].get("type") == "timeseries":
            print("  - Time-series collection already exists")
        else:
            print("  - Warning: Collection exists but is not a time-series collection")
            print("    To convert, drop and recreate: db.metrics_history.drop()")

        metrics_history = db[collection_name]
    else:
        # Create time-series collection
        try:
            db.create_collection(
                collection_name,
                timeseries={
                    "timeField": "timestamp",
                    "metaField": "slug",
                    "granularity": "hours"
                }
            )
            print("  - Created time-series collection (granularity: hours)")
        except (CollectionInvalid, OperationFailure) as e:
            print(f"  - Warning: Could not create time-series collection: {e}")
            print("    Creating as regular collection instead...")
            db.create_collection(collection_name)

        metrics_history = db[collection_name]

    # Create indexes (time-series collections auto-create index on timeField)
    try:
        metrics_history.create_index([("slug", ASCENDING), ("timestamp", DESCENDING)], name="slug_ts_idx")
        print("  - Created index: slug_ts_idx")
    except OperationFailure:
        print("  - Time-series collection manages its own indexes")

    print(f"  - Documents: {metrics_history.count_documents({})}")


def setup_knowledge_collection(db):
    """Create or update the knowledge collection with schema validation and vector index."""
    print("\n[3/3] Setting up 'knowledge' collection (RAG store)...")

    collection_name = "knowledge"

    # Check if collection exists
    if collection_name in db.list_collection_names():
        # Update existing collection with schema validation
        try:
            db.command({
                "collMod": collection_name,
                "validator": KNOWLEDGE_SCHEMA,
                "validationLevel": "moderate",
                "validationAction": "warn"
            })
            print("  - Updated schema validation (moderate level)")
        except OperationFailure as e:
            print(f"  - Warning: Could not update validation: {e}")
    else:
        # Create new collection with validation
        try:
            db.create_collection(
                collection_name,
                validator=KNOWLEDGE_SCHEMA,
                validationLevel="moderate",
                validationAction="warn"
            )
            print("  - Created collection with schema validation")
        except CollectionInvalid as e:
            print(f"  - Warning: {e}")

    knowledge = db[collection_name]

    # Create standard indexes
    knowledge.create_index([("company_slug", ASCENDING)], name="company_slug_idx")
    knowledge.create_index([("company_slug", ASCENDING), ("source", ASCENDING)], name="slug_source_idx")
    knowledge.create_index([("source", ASCENDING)], name="source_idx")

    print("  - Created indexes: company_slug_idx, slug_source_idx, source_idx")

    # Create Atlas Vector Search Index
    create_vector_search_index(knowledge)

    print(f"  - Documents: {knowledge.count_documents({})}")


def create_vector_search_index(collection):
    """
    Programmatically create the Atlas Vector Search index.

    This uses the create_search_index method available in PyMongo 4.4+.
    The index is required for the RAG pipeline's vector similarity search.
    """
    print("  - Setting up Atlas Vector Search index...")

    index_name = "vector_index"

    try:
        # Check if index already exists
        existing_indexes = list(collection.list_search_indexes())
        existing_names = [idx.get("name") for idx in existing_indexes]

        if index_name in existing_names:
            print(f"    Vector search index '{index_name}' already exists")
            return

        # Create the vector search index
        from pymongo.operations import SearchIndexModel

        search_index_model = SearchIndexModel(
            definition=VECTOR_INDEX_DEFINITION,
            name=index_name,
            type="vectorSearch"
        )

        collection.create_search_index(model=search_index_model)
        print(f"    Created vector search index '{index_name}'")
        print("    Note: Index may take a few minutes to become active in Atlas")

    except AttributeError:
        # PyMongo version doesn't support create_search_index
        print("    Warning: PyMongo version doesn't support create_search_index()")
        print("    Please create the vector index manually in MongoDB Atlas UI:")
        print(f"      - Index name: '{index_name}'")
        print("      - Collection: 'knowledge'")
        print("      - Definition:")
        print("        {")
        print('          "fields": [')
        print('            {"type": "vector", "path": "vector", "numDimensions": 384, "similarity": "cosine"},')
        print('            {"type": "filter", "path": "company_slug"}')
        print("          ]")
        print("        }")

    except OperationFailure as e:
        if "already exists" in str(e).lower():
            print(f"    Vector search index '{index_name}' already exists")
        elif "not supported" in str(e).lower() or "atlas" in str(e).lower():
            print("    Warning: Vector search indexes require MongoDB Atlas")
            print("    Please create the index in the Atlas UI if using Atlas")
        else:
            print(f"    Warning: Could not create vector search index: {e}")

    except Exception as e:
        print(f"    Warning: Could not create vector search index: {e}")
        print("    You may need to create it manually in MongoDB Atlas UI")


def print_summary(db):
    """Print a summary of the database setup."""
    print("\n" + "=" * 60)
    print("Database Schema Setup Complete")
    print("=" * 60)

    print("\nCollections:")
    for name in sorted(db.list_collection_names()):
        if not name.startswith("system."):
            count = db[name].count_documents({})
            print(f"  - {name}: {count} documents")

    print("\nSchema Validation:")
    print("  - companies: Required fields (slug, name, metrics, watchlist)")
    print("    - metrics.signal_strength: 0-100 integer")
    print("    - metrics.sentiment: positive/neutral/negative")
    print("    - metrics.burn_rate: low/medium/high/critical")
    print("  - knowledge: Required fields (company_slug, vector, text, source)")

    print("\nSearch Indexes:")
    print("  - companies: Full-text search on name, description")
    print("  - knowledge: Atlas Vector Search (384 dimensions, cosine similarity)")

    print("\nNext Steps:")
    print("  1. Verify vector index is active in Atlas UI (may take a few minutes)")
    print("  2. Run the application: python -m app.main")
    print("  3. Test the RAG pipeline with a company search")


def main():
    """Main entry point for database schema setup."""
    print("=" * 60)
    print("MongoDB Schema Setup for Signals")
    print("=" * 60)

    try:
        # Connect to MongoDB
        print(f"\nConnecting to MongoDB...")
        client = MongoClient(settings.mongodb_uri)
        db = client["signals"]

        # Verify connection
        client.admin.command("ping")
        print(f"Connected to database: {db.name}")

        # Setup collections
        setup_companies_collection(db)
        setup_metrics_history_collection(db)
        setup_knowledge_collection(db)

        # Print summary
        print_summary(db)

        return True

    except Exception as e:
        print(f"\nError during setup: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
