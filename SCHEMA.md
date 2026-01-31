# MongoDB Schema Documentation

## Database: `signals`

### Collection: `companies`

Stores company intelligence profiles with all gathered data.

**Schema:**
```javascript
{
  "_id": ObjectId,
  "slug": String,              // Unique identifier (e.g., "anthropic")
  "name": String,               // Company name (e.g., "Anthropic")
  "description": String,        // AI-generated summary
  "website": String,           // Company website URL
  "watchlist": Boolean,        // User watchlist flag
  "crawled_at": DateTime,      // First crawl timestamp
  "updated_at": DateTime,      // Last update timestamp
  "web_data": {                // Data from Firecrawl
    "url": String,
    "homepage": String,         // Full homepage markdown
    "news": [String],          // News snippets
    "raw": String              // Combined context for RAG
  },
  "document_data": {           // Data from Reducto (optional)
    "extracted_text": String,
    "raw": Object              // Full Reducto response
  },
  "analysis": {                // AI analysis from OpenRouter
    "name": String,
    "summary": String,
    "website": String,
    // ... other AI-extracted fields
  }
}
```

**Indexes:**
- `slug` (unique)`
- `name, description` (text search)`
- `watchlist`
- `updated_at` (descending)
- `crawled_at` (descending)

---

### Collection: `snapshots`

Stores historical snapshots of company data for time-series analysis.

**Schema:**
```javascript
{
  "_id": ObjectId,
  "slug": String,              // Company slug
  "ts": DateTime,              // Snapshot timestamp (UTC)
  "data": {                     // Full snapshot data
    "web_data": Object,
    "document_data": Object,
    "analysis": Object
  }
}
```

**Indexes:**
- `slug, ts` (compound, descending on ts)
- `ts` (descending)

---

### Collection: `knowledge`

Stores vector embeddings for RAG (Retrieval Augmented Generation).

**Schema:**
```javascript
{
  "_id": ObjectId,
  "company_slug": String,       // Links to company
  "text": String,               // Text chunk (500 chars avg)
  "vector": [Number],          // Embedding vector (384-dim)
  "source": String,            // "web" or "document"
  "chunk_index": Number        // Position in original text
}
```

**Indexes:**
- `company_slug, source` (compound)
- `company_slug`
- `source`
- `chunk_index`
- `vector` (vector search index - created in Atlas UI)
  - Index name: `vector_index`
  - Dimensions: 384
  - Filter fields: `company_slug`, `source`

---

## Metrics & Analytics

### Company Metrics (from `companies` collection)

**Basic Metrics:**
- Total companies: `db.companies.countDocuments({})`
- Watchlist companies: `db.companies.countDocuments({watchlist: true})`
- Companies crawled in last 24h: `db.companies.countDocuments({crawled_at: {$gte: yesterday}})`

**Data Quality Metrics:**
- Companies with web data: `db.companies.countDocuments({"web_data.raw": {$exists: true, $ne: ""}})`
- Companies with documents: `db.companies.countDocuments({"document_data": {$ne: null}})`
- Companies with analysis: `db.companies.countDocuments({"analysis.summary": {$exists: true}})`

### RAG Metrics (from `knowledge` collection)

**Storage Metrics:**
- Total chunks: `db.knowledge.countDocuments({})`
- Chunks per company: `db.knowledge.aggregate([{$group: {_id: "$company_slug", count: {$sum: 1}}}])`
- Chunks by source: `db.knowledge.aggregate([{$group: {_id: "$source", count: {$sum: 1}}}])`

**Vector Search Metrics:**
- Average vector search score (from query results)
- Query success rate
- Top retrieved sources

### Snapshot Metrics (from `snapshots` collection)

**Historical Metrics:**
- Total snapshots: `db.snapshots.countDocuments({})`
- Snapshots per company: `db.snapshots.aggregate([{$group: {_id: "$slug", count: {$sum: 1}}}])`
- Snapshots over time: `db.snapshots.aggregate([{$group: {_id: {$dateToString: {format: "%Y-%m-%d", date: "$ts"}}, count: {$sum: 1}}}])`

---

## API Response Format

### GET /api/companies

Returns list of companies with serialized data:

```json
{
  "companies": [
    {
      "_id": "string",           // ObjectId as string
      "slug": "anthropic",
      "name": "Anthropic",
      "description": "...",
      "website": "https://...",
      "watchlist": false,
      "crawled_at": "2026-01-31T...",
      "updated_at": "2026-01-31T...",
      "web_data": {...},
      "document_data": {...},
      "analysis": {...}
    }
  ]
}
```

### GET /api/companies/{slug}

Returns single company profile (same format as above).

### RAG Query Response

```json
{
  "results": [
    {
      "text": "chunk text...",
      "source": "web",
      "score": 0.8542
    }
  ]
}
```

---

## Notes

1. **Vector Search**: Requires MongoDB Atlas with vector search index configured in UI
2. **Text Search**: Uses MongoDB text indexes on `name` and `description` fields
3. **ObjectId Serialization**: All ObjectIds are converted to strings in API responses
4. **Timestamps**: All timestamps are stored in UTC
5. **Slug Generation**: Slugs are generated from company names (lowercase, hyphenated)

