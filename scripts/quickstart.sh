#!/bin/bash
set -e

echo ""
echo "🚀 Signals — Hackathon Setup"
echo "═══════════════════════════════"
echo ""

# ── .env ──
if [ ! -f .env ]; then
  cp .env.example .env
  echo "📋 Created .env from template."
  echo ""
  echo "   ⚠️  Fill in your API keys in .env, then re-run this script."
  echo ""
  echo "   FIRECRAWL_API_KEY   → Firecrawl booth"
  echo "   REDUCTO_API_KEY     → Reducto booth"
  echo "   OPENROUTER_API_KEY  → OpenRouter booth"
  echo "   MONGODB_URI         → mongodb.com/atlas (free cluster)"
  echo "   RESEND_API_KEY      → Resend booth"
  echo ""
  exit 0
fi

# ── Python venv ──
if [ ! -d ".venv" ]; then
  echo "🐍 Creating virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate
echo "🐍 Virtual environment active"

# ── Install deps ──
echo "📦 Installing dependencies..."
pip install -q -r requirements.txt

# ── Check keys ──
echo ""
echo "🔑 API key check:"
set -a && source .env && set +a

check() { [ -z "$2" ] && echo "   ❌ $1" || echo "   ✅ $1"; }

check "FIRECRAWL_API_KEY" "$FIRECRAWL_API_KEY"
check "REDUCTO_API_KEY" "$REDUCTO_API_KEY"
check "OPENROUTER_API_KEY" "$OPENROUTER_API_KEY"
check "MONGODB_URI" "$MONGODB_URI"
check "RESEND_API_KEY" "$RESEND_API_KEY"

echo ""
echo "═══════════════════════════════"
echo "✅ Ready! Next steps:"
echo ""
echo "  1. Start the backend:"
echo "     source .venv/bin/activate"
echo "     uvicorn app.main:app --reload --port 3001"
echo ""
echo "  2. Expose to Lovable (separate terminal):"
echo "     ngrok http 3001"
echo "     # or: cloudflared tunnel --url http://localhost:3001"
echo ""
echo "  3. Test the pipeline:"
echo "     python scripts/test_pipeline.py"
echo ""
echo "  4. Open Lovable → paste the ngrok URL → build the frontend"
echo ""
echo "  Claude Code commands:"
echo "     /hackathon  — full context"
echo "     /pipeline   — API patterns"
echo "     /lovable    — frontend prompts"
echo "     /demo       — demo prep"
echo ""
