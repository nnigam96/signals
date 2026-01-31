import json
import logging
from typing import Any, AsyncGenerator
import httpx
from app.config import settings

logger = logging.getLogger(__name__)
OPENROUTER_BASE = "https://openrouter.ai/api/v1"
MODEL = "anthropic/claude-sonnet-4-20250514"  # Or use "anthropic/claude-3-5-sonnet"

def _headers():
    return {"Authorization": f"Bearer {settings.openrouter_api_key}", "Content-Type": "application/json"}

async def analyze_company(name, url, web_data, document_data) -> dict[str, Any]:
    # Prepare context
    web_txt = str(web_data)[:8000]
    doc_txt = str(document_data)[:4000] if document_data else ""
    
    system_prompt = """You are a market intelligence engine. 
    Analyze the provided data and return a valid JSON object with:
    {
      "name": "Company Name",
      "summary": "2 sentence pitch",
      "pmf_score": 1-10 (int),
      "competitors": ["Comp1", "Comp2"],
      "strengths": ["..."],
      "red_flags": ["..."],
      "funding": "Unknown or $X M",
      "website": "url"
    }
    """
    
    user_prompt = f"Analyze {name or url}.\n\nWEB:\n{web_txt}\n\nDOCS:\n{doc_txt}"

    async with httpx.AsyncClient(timeout=90) as client:
        res = await client.post(
            f"{OPENROUTER_BASE}/chat/completions",
            headers=_headers(),
            json={
                "model": MODEL,
                "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                "response_format": {"type": "json_object"}
            }
        )
    
    if res.status_code != 200:
        logger.error(f"OpenRouter failed: {res.text}")
        return {"name": name, "summary": "Analysis failed"}

    try:
        content = res.json()["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception:
        return {"name": name, "summary": content[:200]}

async def chat_with_context(message: str, context: list[dict]) -> AsyncGenerator[str, None]:
    # Simple RAG streaming
    context_str = "\n".join([f"- {c.get('name')}: {c.get('description')}" for c in context])
    
    async with httpx.AsyncClient() as client:
        async with client.stream("POST", f"{OPENROUTER_BASE}/chat/completions", 
            headers=_headers(),
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": f"Answer based on:\n{context_str}"},
                    {"role": "user", "content": message}
                ],
                "stream": True
            }
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: ") and line != "data: [DONE]":
                    try:
                        chunk = json.loads(line[6:])
                        if delta := chunk["choices"][0]["delta"].get("content"):
                            yield delta
                    except: pass