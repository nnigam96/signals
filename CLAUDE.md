# Signals — AI-Powered Market Intelligence

## What This Is
A real-time market intelligence platform built at Hack the Stackathon (Jan 31, 2026, YC HQ).
Two interfaces: a chat/search for deep dives, and a monitoring dashboard for tracking companies over time.
Frontend built with Lovable (hosted React). Backend is Python (FastAPI). No TypeScript anywhere.

## Architecture

```
Lovable Frontend (hosted by Lovable)
    │
    │  HTTPS
    ▼
ngrok / cloudflared tunnel
    │
    │  forwards to
    ▼
FastAPI Backend (localhost:3001)
    │
    ├── POST /api/chat ──────► chat/handler.py (intent classification)
    │                              │
    │                              ├── MongoDB hit? → respond from stored data
    │                              └── MongoDB miss? → trigger pipeline
    │
    ├── POST /api/analyze ───► pipeline/orchestrator.py
    │                              │
    │                              ├─► firecrawl.py  (crawl web)
    │                              ├─► reducto.py    (parse docs)
    │                              ├─► openrouter.py (AI analysis)
    │                              ├─► mongodb.py    (store profile)
    │                              └─► resend.py     (email alerts)
    │
    ├── GET  /api/companies
    ├── GET  /api/companies/{slug}
    ├── GET  /api/companies/search?q=
    └── POST /api/watchlist
           │
           ▼
    MongoDB Atlas (cloud)
```

## Tech Stack
- **Backend**: Python 3.11+ / FastAPI / uvicorn
- **HTTP client**: httpx (async)
- **Database**: MongoDB Atlas via pymongo
- **Frontend**: Lovable (hosted React — we don't manage this code)
- **Tunnel**: ngrok or cloudflared (exposes localhost to Lovable)
- **APIs**: Firecrawl, Reducto, OpenRouter, Resend
- **Stretch**: Supabase Realtime, Algolia search, ElevenLabs, Mux

## File Structure
```
signals/
├── CLAUDE.md                  # You're reading this
├── .claude/commands/          # Slash commands for Claude Code
│   ├── hackathon.md           # /hackathon — context, judges, deadlines
│   ├── pipeline.md            # /pipeline  — API patterns, debugging
│   ├── lovable.md             # /lovable   — frontend prompts for Lovable
│   └── demo.md                # /demo      — demo script, checklist
├── app/
│   ├── main.py                # FastAPI app + startup
│   ├── config.py              # pydantic-settings (.env loader)
│   ├── pipeline/
│   │   ├── firecrawl.py       # Firecrawl API (crawl + search)
│   │   ├── reducto.py         # Reducto API (doc parsing)
│   │   ├── openrouter.py      # OpenRouter API (LLM + streaming)
│   │   ├── mongodb.py         # All DB ops (pymongo)
│   │   ├── resend_alerts.py   # Resend email notifications
│   │   └── orchestrator.py    # Wires the pipeline together
│   ├── api/
│   │   └── routes.py          # FastAPI endpoints + SSE
│   └── chat/
│       └── handler.py         # Intent classification + query routing
├── requirements.txt
├── .env.example
├── .gitignore
├── Procfile                   # For Railway/Render deployment
└── scripts/
    ├── quickstart.sh          # Setup script
    └── test_pipeline.py       # Quick smoke test
```

## Running Locally
```bash
source .venv/bin/activate
uvicorn app.main:app --reload --port 3001
```

## Exposing to Lovable
```bash
# In a separate terminal
ngrok http 3001
# Copy the https://xxxxx.ngrok.io URL → use in Lovable frontend
```

## Code Conventions
- Type hints on everything
- async/await for all external HTTP calls
- Every external API call wrapped in try/except — pipeline never crashes
- Logging via `logging.getLogger(__name__)`, not print()
- Settings from `app.config.settings` (loaded from .env via pydantic-settings)
- MongoDB documents use snake_case keys
- All times stored as UTC datetime
