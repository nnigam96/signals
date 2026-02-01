# Signals AI Agent Command

Use this command to interact with the Signals API through Claude Code.

## Quick Start

The agent script is located at `scripts/signals_agent.py`. You can use it directly or reference it in Claude Code.

## Commands

### Analyze Company
```bash
python scripts/signals_agent.py analyze Anthropic
```
Runs the full pipeline: Firecrawl → Reducto → AI Analysis → RAG storage

### Search Companies
```bash
python scripts/signals_agent.py search "AI company"
```
Searches the database for companies matching the query

### Get Company Details
```bash
python scripts/signals_agent.py company anthropic
```
Retrieves full company profile with all data

### Get Highlights
```bash
# Single company
python scripts/signals_agent.py highlights anthropic

# All companies
python scripts/signals_agent.py highlights
```
Gets key metrics and signal highlights

### Chat with RAG
```bash
python scripts/signals_agent.py chat "What are Anthropic's main products?"
```
Queries the RAG system for insights

### Vector Scores
```bash
python scripts/signals_agent.py vector-scores anthropic
```
Gets AI-calculated vector scores (Market Momentum, Hiring, Product, etc.)

### List Companies
```bash
# All companies
python scripts/signals_agent.py list

# Watchlist only
python scripts/signals_agent.py list --watchlist
```

## Configuration

Set environment variable:
```bash
export SIGNALS_API_URL=http://localhost:3001
```

Or use `--base-url` flag:
```bash
python scripts/signals_agent.py --base-url http://localhost:3001 analyze Anthropic
```

## Integration with Claude Code

You can reference this agent in Claude Code by:

1. **Direct execution**: Ask Claude to run the agent script
2. **Custom command**: Add to your Claude Code commands
3. **Tool integration**: Use as a tool in Claude Code workflows

Example Claude Code usage:
```
"Run the Signals agent to analyze OpenAI"
→ Claude executes: python scripts/signals_agent.py analyze OpenAI
```

## Output Format

The agent provides:
- ✅ Success indicators
- ❌ Error messages
- 📊 Formatted data
- 💡 Helpful tips

All responses are JSON-compatible for programmatic use.

