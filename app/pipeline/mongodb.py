import logging
import re
from datetime import datetime, timezone
from pymongo import MongoClient, TEXT
from app.config import settings

logger = logging.getLogger(__name__)
_client = None
_db = None

def connect_db():
    global _client, _db
    if not _client:
        _client = MongoClient(settings.mongodb_uri)
        _db = _client["signals"]
        # Create indexes
        _db.companies.create_index("slug", unique=True)
        _db.companies.create_index([("name", TEXT), ("description", TEXT)])
        logger.info("[mongodb] Connected")

def _co(): return _db.companies
def _sn(): return _db.snapshots

def make_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

def store_company(data):
    slug = data["slug"]
    return _co().find_one_and_update(
        {"slug": slug}, 
        {"$set": data}, 
        upsert=True, 
        return_document=True
    )

def get_company(slug): return _co().find_one({"slug": slug})
def list_companies(watchlist_only=False):
    q = {"watchlist": True} if watchlist_only else {}
    return list(_co().find(q).sort("updated_at", -1))

def search_companies(q):
    return list(_co().find({"$text": {"$search": q}}).limit(10))

def store_snapshot(slug, data):
    _sn().insert_one({"slug": slug, "data": data, "ts": datetime.now(timezone.utc)})

def toggle_watchlist(slug, enabled):
    _co().update_one({"slug": slug}, {"$set": {"watchlist": enabled}})

def get_knowledge_collection() -> Collection:
    assert _db is not None, "Call connect_db() first"
    return _db["knowledge"]

def search_knowledge(query: str, company_slug: str = None, limit: int = 5):
    """
    Performs a Vector Search on the 'knowledge' collection.
    """
    # Lazy import to avoid circular dependency
    from app.pipeline.rag import embedding_model 
    
    # 1. Embed the user's question
    # This returns a generator, so we take the first item
    query_vector = list(embedding_model.embed([query]))[0].tolist()
    
    # 2. Vector Search Pipeline
    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index",       # We will create this in Atlas UI
                "path": "vector",
                "queryVector": query_vector,
                "numCandidates": 100,          # How many neighbors to consider
                "limit": limit                 # How many to return
            }
        },
        {
            "$project": {
                "_id": 0,
                "text": 1,
                "source": 1,
                "score": {"$meta": "vectorSearchScore"}
            }
        }
    ]

    # Optional: Filter by specific company
    # Note: For this to work, 'company_slug' must be defined as a filter field in Atlas
    if company_slug:
        pipeline[0]["$vectorSearch"]["filter"] = {"company_slug": company_slug}

    return list(get_knowledge_collection().aggregate(pipeline))