import logging
import re
from datetime import datetime, timezone
from typing import List, Any

from pymongo import MongoClient, TEXT, ASCENDING, DESCENDING
from pymongo.errors import OperationFailure

# SearchIndexModel is only available in pymongo 4.4+
try:
    from pymongo.operations import SearchIndexModel
    HAS_SEARCH_INDEX = True
except ImportError:
    HAS_SEARCH_INDEX = False

from app.config import settings

logger = logging.getLogger(__name__)

_client = None
_db = None


def connect_db():
    """Initialize MongoDB connection and indexes."""
    global _client, _db
    if not _client:
        try:
            _client = MongoClient(settings.mongodb_uri)
            _client.admin.command('ping')
            # Try to get default database from URI, fall back to 'signals'
            try:
                _db = _client.get_default_database()
            except Exception:
                _db = _client["signals"]
            logger.info(f"Connected to MongoDB: {_db.name}")
            _init_indexes()
        except Exception as e:
            logger.error(f"MongoDB Connection Failed: {e}")
            raise e


def _init_indexes():
    """Idempotent creation of indexes."""
    try:
        # Companies collection
        _safe_create_index(_db.companies, "slug", unique=True, name="slug_unique")
        _safe_create_index(_db.companies, "watchlist", name="watchlist_idx")
        _safe_create_index(_db.companies, [("name", TEXT), ("description", TEXT)], name="text_search")
        _safe_create_index(_db.companies, [("updated_at", DESCENDING)], name="updated_at_idx")

        # Snapshots collection
        _safe_create_index(_db.snapshots, [("slug", ASCENDING), ("timestamp", DESCENDING)], name="slug_ts_idx")

        # Knowledge collection (RAG)
        _safe_create_index(_db.knowledge, "company_slug", name="company_slug_idx")
        _safe_create_index(_db.knowledge, [("company_slug", ASCENDING), ("source", ASCENDING)], name="slug_source_idx")

        # Attempt programmatic vector index creation (Atlas only, pymongo 4.4+)
        if HAS_SEARCH_INDEX:
            try:
                index_model = SearchIndexModel(
                    definition={
                        "fields": [
                            {"type": "vector", "path": "vector", "numDimensions": 384, "similarity": "cosine"},
                            {"type": "filter", "path": "company_slug"}
                        ]
                    },
                    name="vector_search",
                    type="vectorSearch"
                )
                _db.knowledge.create_search_index(model=index_model)
                logger.info("Created vector search index")
            except Exception:
                pass  # Index likely exists or not on Atlas

        logger.info("Indexes initialized")
    except Exception as e:
        logger.warning(f"Index initialization warning: {e}")


def _safe_create_index(collection, keys, **kwargs):
    """Create index, ignoring if it already exists."""
    try:
        collection.create_index(keys, **kwargs)
    except OperationFailure as e:
        if "already exists" not in str(e) and "IndexOptionsConflict" not in str(e):
            raise


def _co():
    """Get companies collection."""
    if _db is None:
        connect_db()
    return _db.companies


def _sn():
    """Get snapshots collection."""
    if _db is None:
        connect_db()
    return _db.snapshots


def _kn():
    """Get knowledge collection."""
    if _db is None:
        connect_db()
    return _db.knowledge


def _mh():
    """Get metrics_history collection."""
    if _db is None:
        connect_db()
    return _db.metrics_history


def make_slug(name: str) -> str:
    """Generate URL-safe slug from company name."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# --- Company Operations ---

def store_company(data: dict) -> dict:
    """Upsert a company document."""
    slug = data.get("slug") or make_slug(data.get("name", "unknown"))
    data["slug"] = slug
    data["updated_at"] = datetime.now(timezone.utc)

    return _co().find_one_and_update(
        {"slug": slug},
        {"$set": data},
        upsert=True,
        return_document=True
    )


def get_company(slug: str) -> dict | None:
    """Retrieve a company by slug."""
    return _co().find_one({"slug": slug})


def list_companies(watchlist_only: bool = False) -> list:
    """List all companies, optionally filtered to watchlist."""
    q = {"watchlist": True} if watchlist_only else {}
    return list(_co().find(q).sort("updated_at", -1))


def search_companies(query: str) -> list:
    """Full-text search on companies."""
    return list(_co().find({"$text": {"$search": query}}).limit(10))


def toggle_watchlist(slug: str, enabled: bool):
    """Toggle watchlist status for a company."""
    _co().update_one({"slug": slug}, {"$set": {"watchlist": enabled}})


# --- Snapshot Operations ---

def store_snapshot(slug: str, data: dict):
    """Store a point-in-time snapshot of company data."""
    _sn().insert_one({
        "slug": slug,
        "timestamp": datetime.now(timezone.utc),
        "data": data
    })


# --- Metrics History (Time Series) ---

def record_metric_history(slug: str, metrics: dict):
    """Store metrics in the time-series collection."""
    if not metrics:
        return
    doc = {
        "slug": slug,
        "timestamp": datetime.now(timezone.utc),
        **metrics
    }
    _mh().insert_one(doc)
    logger.debug(f"Recorded metrics for {slug}")


def get_metric_history(slug: str, limit: int = 30) -> list:
    """Retrieve metric history for a company."""
    return list(
        _mh()
        .find({"slug": slug})
        .sort("timestamp", -1)
        .limit(limit)
    )


# --- Knowledge / RAG Operations ---

def get_knowledge_collection():
    """Get the knowledge collection for RAG."""
    if _db is None:
        connect_db()
    return _db.knowledge


def store_knowledge(docs: list[dict]):
    """Bulk insert knowledge documents."""
    if docs:
        _kn().insert_many(docs)


def delete_knowledge(company_slug: str, source: str = None):
    """Delete knowledge docs for a company, optionally by source."""
    query = {"company_slug": company_slug}
    if source:
        query["source"] = source
    _kn().delete_many(query)


def search_knowledge_by_vector(query_vector: List[float], company_slug: str = None, limit: int = 5) -> list:
    """
    Perform Atlas Vector Search on the knowledge collection.
    Returns documents with text, source, and similarity score.
    """
    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_search",
                "path": "vector",
                "queryVector": query_vector,
                "numCandidates": limit * 10,
                "limit": limit
            }
        },
        {
            "$project": {
                "_id": 0,
                "text": 1,
                "source": 1,
                "company_slug": 1,
                "score": {"$meta": "vectorSearchScore"}
            }
        }
    ]

    if company_slug:
        pipeline[0]["$vectorSearch"]["filter"] = {"company_slug": company_slug}

    return list(_kn().aggregate(pipeline))


def search_knowledge(query: str, company_slug: str = None, limit: int = 5) -> list:
    """
    Convenience function: embeds query and performs vector search.
    """
    from app.pipeline.rag import embedding_model

    query_vector = list(embedding_model.embed([query]))[0].tolist()
    return search_knowledge_by_vector(query_vector, company_slug, limit)
