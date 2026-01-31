# Project Summary - Signals Platform

## Overview
AI-powered market intelligence platform that crawls company data, extracts insights, and stores them in a searchable knowledge base using RAG (Retrieval Augmented Generation).

---

## What's Been Built

### 1. Core Pipeline (`app/pipeline/`)

#### **Firecrawl Integration** (`firecrawl.py`)
- **Company URL Discovery**: Automatically finds company websites from names
- **Web Scraping**: Scrapes homepage, news, and market information
- **Parallel Execution**: Fetches homepage, news, and market data simultaneously
- **Data Sources**:
  - Homepage (full markdown)
  - News snippets (latest funding, news 2025-2026)
  - Market info (competitors, pricing)
  - Techmeme integration (ready to add)

#### **Reducto Integration** (`reducto.py`)
- **Document Parsing**: Parses PDFs and documents
- **Two-step Process**: Upload → Parse workflow
- **Base64 Support**: Handles base64-encoded documents
- **URL Support**: Can parse documents from URLs
- **Text Extraction**: Extracts structured text from PDFs

#### **OpenRouter Integration** (`openrouter.py`)
- **AI Analysis**: Analyzes company data using LLM
- **Streaming Chat**: SSE-based chat with context
- **Company Summarization**: Generates company summaries and insights

#### **RAG System** (`rag.py`)
- **Text Chunking**: Splits text into 500-char chunks
- **Vector Embeddings**: Uses BAAI/bge-small-en-v1.5 (384-dim)
- **Knowledge Storage**: Stores chunks with embeddings in MongoDB
- **Source Tracking**: Tracks "web" vs "document" sources

#### **MongoDB Integration** (`mongodb.py`)
- **Three Collections**:
  - `companies`: Company profiles
  - `snapshots`: Historical data
  - `knowledge`: Vector embeddings
- **Text Search**: Full-text search on company names/descriptions
- **Vector Search**: Semantic search via MongoDB Atlas
- **Watchlist**: User watchlist functionality

#### **Orchestrator** (`orchestrator.py`)
- **Parallel Pipeline**: Runs Firecrawl + Reducto in parallel
- **RAG Integration**: Automatically stores data in RAG
- **Error Handling**: Graceful error handling throughout
- **Company Refresh**: Re-run pipeline for existing companies

---

### 2. API Endpoints (`app/api/routes.py`)

- `POST /api/chat` - Streaming chat with SSE
- `POST /api/analyze` - Trigger full pipeline
- `POST /api/analyze/{slug}/refresh` - Refresh company data
- `GET /api/companies` - List all companies (with watchlist filter)
- `GET /api/companies/search?q=` - Search companies
- `GET /api/companies/{slug}` - Get single company
- `POST /api/watchlist` - Toggle watchlist
- `GET /health` - Health check

---

### 3. Testing & Inspection Scripts (`scripts/`)

#### **Inspection Scripts**
- `inspect_firecrawl.py` - Test Firecrawl API (search, scrape, full crawl)
- `inspect_reducto.py` - Test Reducto API (upload, parse)
- `inspect_rag.py` - Test RAG system (chunking, embedding, storage, search)

#### **Integration Tests**
- `test_firecrawl_rag_integration.py` - Full integration test:
  - Company name → Firecrawl → RAG → Query → Metrics
  - Collects timing, RAG, and query metrics
  - Saves results to JSON

#### **Compatibility Tests**
- `test_mongodb_compatibility.py` - MongoDB compatibility test:
  - Connection test
  - CRUD operations
  - Vector search (if available)
  - Index verification

#### **Database Scripts**
- `verify_db.py` - Simple MongoDB connection test (uses dotenv)
- `init_mongodb.py` - Initialize collections and indexes

---

### 4. Database Schema

**Collections:**
1. **companies** - Company profiles with web_data, document_data, analysis
2. **snapshots** - Historical snapshots with timestamps
3. **knowledge** - Vector embeddings for RAG (384-dim vectors)

**Indexes:**
- Text search on companies (name, description)
- Unique slug index
- Vector search index (requires Atlas UI setup)
- Time-based indexes for snapshots

See `SCHEMA.md` for full documentation.

---

## Key Features Implemented

### ✅ Data Ingestion
- Web crawling via Firecrawl
- Document parsing via Reducto
- Parallel execution for speed

### ✅ AI Processing
- Company analysis via OpenRouter
- Streaming chat responses
- Context-aware queries

### ✅ RAG System
- Automatic chunking and embedding
- Vector storage in MongoDB
- Semantic search capabilities

### ✅ Data Storage
- Company profiles in MongoDB
- Historical snapshots
- Vector embeddings for search

### ✅ API Layer
- RESTful endpoints
- SSE streaming
- Error handling

### ✅ Testing Infrastructure
- Individual service tests
- Integration tests
- Compatibility tests
- Metrics collection

---

## Metrics Available

### From Integration Test (`test_firecrawl_rag_integration.py`)

**Timing Metrics:**
- Firecrawl time
- RAG storage time
- Query execution time
- Total pipeline time

**RAG Metrics:**
- Chunks created
- Chunks stored
- Average chunk size
- Storage success rate

**Query Metrics:**
- Results per query
- Average similarity score
- Query success rate
- Top result previews

### From MongoDB Collections

**Company Metrics:**
- Total companies
- Watchlist count
- Companies with web data
- Companies with documents
- Companies with analysis

**RAG Metrics:**
- Total chunks
- Chunks per company
- Chunks by source (web/document)
- Vector search performance

**Snapshot Metrics:**
- Total snapshots
- Snapshots per company
- Time-series data

---

## Next Steps for Lovable Integration

### 1. Reverse Engineer Metrics from Mockup

Based on your Lovable mockup, identify:
- **Dashboard Metrics**: What KPIs are displayed?
- **Table Columns**: What data columns are shown?
- **Filters**: What filters are available?
- **Charts**: What visualizations are needed?

### 2. Map Metrics to Database

Create mapping between:
- Mockup metrics → MongoDB queries
- Table columns → Collection fields
- Filters → MongoDB query filters

### 3. Create API Endpoints

Add endpoints for:
- Metrics aggregation
- Time-series data
- Filtered queries
- Dashboard data

### 4. Update Schema if Needed

Based on mockup requirements:
- Add new fields to collections
- Create new collections if needed
- Add indexes for performance

---

## How to Use

### Initialize Database
```bash
python scripts/init_mongodb.py
```

### Test MongoDB Connection
```bash
python scripts/verify_db.py
```

### Run Integration Test
```bash
python scripts/test_firecrawl_rag_integration.py "Company Name"
```

### Test Individual Services
```bash
python scripts/inspect_firecrawl.py "Company Name"
python scripts/inspect_reducto.py path/to/document.pdf
python scripts/inspect_rag.py
```

### Run Compatibility Tests
```bash
python scripts/test_mongodb_compatibility.py
```

### Start API Server
```bash
uvicorn app.main:app --reload --port 3001
```

---

## File Structure

```
signals-1/
├── app/
│   ├── api/
│   │   └── routes.py          # API endpoints
│   ├── chat/
│   │   └── handler.py         # Chat intent handling
│   ├── pipeline/
│   │   ├── firecrawl.py       # Web crawling
│   │   ├── reducto.py         # Document parsing
│   │   ├── openrouter.py      # AI analysis
│   │   ├── mongodb.py         # Database operations
│   │   ├── rag.py             # RAG system
│   │   └── orchestrator.py   # Main pipeline
│   ├── config.py              # Settings
│   └── main.py                # FastAPI app
├── scripts/
│   ├── init_mongodb.py        # Database initialization
│   ├── verify_db.py           # Connection test
│   ├── inspect_*.py           # Service inspection
│   └── test_*.py              # Integration tests
├── SCHEMA.md                  # Database schema docs
└── SUMMARY.md                 # This file
```

---

## Environment Variables Required

```env
# APIs
FIRECRAWL_API_KEY=...
REDUCTO_API_KEY=...
OPENROUTER_API_KEY=...
RESEND_API_KEY=...

# Database
MONGODB_URI=mongodb://localhost:27017/signals
# or for Atlas:
# MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/signals

# Server
PORT=3001
```

---

## Dependencies

See `requirements.txt` for full list. Key packages:
- `fastapi` - API framework
- `httpx` - Async HTTP client
- `pymongo` - MongoDB driver
- `fastembed` - Vector embeddings
- `python-dotenv` - Environment variables
- `pydantic-settings` - Settings management

---

## Current Status

✅ **Complete:**
- All core pipeline services
- RAG system with vector storage
- MongoDB integration
- API endpoints
- Testing infrastructure
- Database initialization

🔄 **Next:**
- Reverse engineer Lovable mockup metrics
- Map metrics to database queries
- Create dashboard API endpoints
- Update schema if needed

---

## Notes

1. **Vector Search**: Requires MongoDB Atlas with vector search index (created in UI)
2. **Local MongoDB**: Works with local MongoDB, but vector search requires Atlas
3. **Techmeme**: Code ready to add, just needs to be uncommented in firecrawl.py
4. **Error Handling**: All services have try/except blocks for graceful failures
5. **Parallel Execution**: Pipeline runs Firecrawl + Reducto in parallel for speed

