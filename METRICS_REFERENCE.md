# Metrics Reference Guide

Quick reference for metrics you can extract from the database to match your Lovable mockup.

## Quick Metrics Queries

### Company Counts
```python
# Total companies
db.companies.count_documents({})

# Watchlist companies
db.companies.count_documents({"watchlist": True})

# Companies with web data
db.companies.count_documents({"web_data.raw": {"$exists": True, $ne: ""}})

# Companies with documents
db.companies.count_documents({"document_data": {"$ne": None}})
```

### RAG Metrics
```python
# Total knowledge chunks
db.knowledge.count_documents({})

# Chunks per company
db.knowledge.aggregate([
    {"$group": {"_id": "$company_slug", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}}
])

# Chunks by source
db.knowledge.aggregate([
    {"$group": {"_id": "$source", "count": {"$sum": 1}}}
])
```

### Time-Based Metrics
```python
# Companies crawled today
from datetime import datetime, timedelta
today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
db.companies.count_documents({"crawled_at": {"$gte": today}})

# Companies updated in last 7 days
week_ago = datetime.now(timezone.utc) - timedelta(days=7)
db.companies.count_documents({"updated_at": {"$gte": week_ago}})
```

### Data Quality Metrics
```python
# Companies with complete data
db.companies.count_documents({
    "web_data.raw": {"$exists": True, "$ne": ""},
    "analysis.summary": {"$exists": True}
})

# Average description length
db.companies.aggregate([
    {"$project": {"desc_len": {"$strLenCP": {"$ifNull": ["$description", ""]}}}},
    {"$group": {"_id": None, "avg_len": {"$avg": "$desc_len"}}}
])
```

## Common Dashboard Metrics

### Overview Dashboard
- Total companies tracked
- Watchlist count
- Companies added today/this week
- Data completeness percentage
- Total knowledge chunks

### Company List Table
Columns to consider:
- Name
- Description (summary)
- Website
- Last updated
- Watchlist status
- Data sources (web/document/both)
- Chunk count

### Company Detail View
- Full company profile
- Web data preview
- Document data (if available)
- Analysis summary
- Historical snapshots
- Related knowledge chunks

## API Endpoints for Metrics

### Suggested Endpoints

```python
# GET /api/metrics/overview
{
  "total_companies": 150,
  "watchlist_count": 25,
  "companies_today": 5,
  "total_chunks": 5000,
  "data_completeness": 0.85
}

# GET /api/metrics/companies
{
  "companies": [...],
  "total": 150,
  "page": 1,
  "per_page": 20
}

# GET /api/metrics/rag
{
  "total_chunks": 5000,
  "chunks_by_source": {
    "web": 3000,
    "document": 2000
  },
  "avg_chunks_per_company": 33.3
}
```

## Mapping Lovable Mockup to Database

### Step 1: Identify Displayed Metrics
Look at your mockup and list:
- What numbers are shown?
- What tables are displayed?
- What filters are available?

### Step 2: Map to Collections
- Company list → `companies` collection
- Metrics → Aggregations on `companies`, `knowledge`, `snapshots`
- Filters → MongoDB query filters

### Step 3: Create Queries
Write MongoDB queries or Python functions that:
- Match the mockup data structure
- Support the filters shown
- Calculate the metrics displayed

### Step 4: Create API Endpoints
Add endpoints that:
- Return data in mockup format
- Support filtering
- Include pagination if needed

## Example: Company List Table

If your mockup shows a table with:
- Company name
- Description
- Last updated
- Watchlist badge

**MongoDB Query:**
```python
companies = db.companies.find({}).sort("updated_at", -1).limit(20)
```

**API Response:**
```json
{
  "companies": [
    {
      "name": "Anthropic",
      "description": "AI safety company...",
      "updated_at": "2026-01-31T...",
      "watchlist": true
    }
  ]
}
```

## Next Steps

1. **Screenshot your Lovable mockup**
2. **List all displayed metrics**
3. **Identify table columns**
4. **Map to database collections**
5. **Create API endpoints**
6. **Test with real data**

