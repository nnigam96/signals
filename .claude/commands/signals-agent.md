# Signals AI Agent

An AI agent that can interact with the Signals API to analyze companies, search for intelligence, and retrieve market insights.

## Usage

```
/signals analyze <company_name>
/signals search <query>
/signals company <slug>
/signals highlights [slug]
/signals chat <message>
```

## Capabilities

- **Company Analysis**: Run full pipeline on a company (Firecrawl + Reducto + AI Analysis)
- **Search**: Search companies in the database
- **Company Details**: Get full company profile with signals
- **Highlights**: Get key metrics and signal highlights
- **Chat**: Query the RAG system for company insights
- **Vector Scores**: Get AI-calculated vector scores for companies

## API Endpoints

The agent uses these endpoints:
- `POST /api/analyze` - Full pipeline analysis
- `GET /api/companies` - List all companies
- `GET /api/companies/search?q=` - Search companies
- `GET /api/company/{slug}` - Get company details
- `GET /api/company/{slug}/highlights` - Get highlights
- `GET /api/highlights` - Get all highlights
- `POST /api/chat` - Chat with RAG system
- `GET /api/companies/{slug}/vector-scores` - Vector scores

## Configuration

Set these environment variables:
- `SIGNALS_API_URL` - API base URL (default: http://localhost:3001)
- Or use the agent script directly with `--base-url`

## Examples

```
/signals analyze Anthropic
/signals search AI
/signals company anthropic
/signals highlights anthropic
/signals chat "What are Anthropic's main products?"
```

