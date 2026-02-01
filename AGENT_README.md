# Signals AI Agent

An intelligent agent for interacting with the Signals API. Can be used standalone or integrated with Claude Code.

## Quick Start

```bash
# Make sure server is running
uvicorn app.main:app --reload --port 3001

# Run agent commands
python scripts/signals_agent.py analyze Anthropic
python scripts/signals_agent.py search "AI"
python scripts/signals_agent.py company anthropic
```

## Available Commands

| Command | Description | Example |
|---------|-------------|---------|
| `analyze` | Run full pipeline on company | `analyze Anthropic` |
| `search` | Search companies | `search "AI company"` |
| `company` | Get company details | `company anthropic` |
| `highlights` | Get highlights (all or specific) | `highlights anthropic` |
| `chat` | Chat with RAG system | `chat "What is Anthropic?"` |
| `vector-scores` | Get AI vector scores | `vector-scores anthropic` |
| `list` | List all companies | `list --watchlist` |

## Using in Claude Code

### Method 1: Direct Reference
Ask Claude to use the agent:
```
"Use the Signals agent to analyze OpenAI"
```

Claude will execute:
```bash
python scripts/signals_agent.py analyze OpenAI
```

### Method 2: Custom Command
Add to Claude Code settings to create a `/signals` command.

### Method 3: Tool Integration
The agent can be used as a tool in Claude Code workflows for:
- Automated company analysis
- Batch processing
- Data extraction
- Report generation

## Configuration

**Environment Variable:**
```bash
export SIGNALS_API_URL=http://localhost:3001
```

**Command Line:**
```bash
python scripts/signals_agent.py --base-url http://localhost:3001 analyze Anthropic
```

## Example Workflow

```bash
# 1. Analyze a company
python scripts/signals_agent.py analyze Anthropic

# 2. Get details
python scripts/signals_agent.py company anthropic

# 3. Get highlights
python scripts/signals_agent.py highlights anthropic

# 4. Get vector scores
python scripts/signals_agent.py vector-scores anthropic

# 5. Chat about it
python scripts/signals_agent.py chat "What are Anthropic's main products?"
```

## Output

The agent provides:
- ✅ Success indicators
- ❌ Clear error messages
- 📊 Formatted data
- 💡 Helpful tips and next steps

All responses are JSON-compatible for programmatic use.

## Integration Examples

### Claude Code Usage
```
User: "Analyze OpenAI using the Signals agent"
Claude: Executes `python scripts/signals_agent.py analyze OpenAI`
        Returns formatted results
```

### Batch Processing
```bash
for company in Anthropic OpenAI Stripe; do
    python scripts/signals_agent.py analyze "$company"
done
```

### Automated Reports
```bash
# Get highlights for all companies
python scripts/signals_agent.py highlights > highlights_report.json
```

