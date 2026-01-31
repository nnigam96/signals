import json
import logging
from typing import Any, AsyncGenerator

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

# Initialize OpenAI-compatible client for OpenRouter
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.openrouter_api_key,
)


async def analyze_company(name: str = None, url: str = None, web_data: Any = None, document_data: Any = None) -> dict:
    """
    Analyze company data using LLM and return structured intelligence.
    """
    # Prepare context from available data
    context_parts = []

    if web_data:
        if isinstance(web_data, dict):
            raw = web_data.get("raw", "")
            if raw:
                context_parts.append(f"=== WEB DATA ===\n{raw[:12000]}")
        else:
            context_parts.append(f"=== WEB DATA ===\n{str(web_data)[:12000]}")

    if document_data:
        if isinstance(document_data, dict):
            doc_text = document_data.get("extracted_text", "")
            if doc_text:
                context_parts.append(f"=== DOCUMENT ===\n{doc_text[:4000]}")
        else:
            context_parts.append(f"=== DOCUMENT ===\n{str(document_data)[:4000]}")

    context = "\n\n".join(context_parts) if context_parts else "No data available."
    identifier = name or url or "Unknown Company"

    prompt = f"""Analyze the following data for {identifier}.

DATA:
{context}

TASK:
Return a JSON object with the following structure:
{{
    "name": "Company Name",
    "summary": "2-3 sentence company description and value proposition",
    "metrics": {{
        "sentiment": "Bullish" | "Bearish" | "Neutral",
        "signal_strength": 0-100 (integer representing confidence/strength of signals),
        "pmf_score": 1-10 (product-market fit score)
    }},
    "competitors": ["Competitor1", "Competitor2"],
    "strengths": ["Key strength 1", "Key strength 2"],
    "red_flags": ["Potential concern 1"],
    "funding": "Unknown" or "$X raised",
    "website": "company website URL"
}}

Output valid JSON only, no markdown formatting.
"""

    try:
        response = await client.chat.completions.create(
            model=settings.model_name,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            timeout=90
        )

        content = response.choices[0].message.content
        return json.loads(content)

    except Exception as e:
        logger.error(f"OpenRouter analysis failed: {e}")
        return {
            "name": identifier,
            "summary": "Analysis failed",
            "metrics": {"sentiment": "Neutral", "signal_strength": 0},
            "error": str(e)
        }


async def chat_with_context(message: str, context: list[dict]) -> AsyncGenerator[str, None]:
    """
    Stream a chat response with RAG context.
    Used for the chatbot interface.
    """
    context_str = "\n".join([
        f"- {c.get('text', '')[:500]}" for c in context
    ])

    system_prompt = f"""You are a market intelligence assistant. Answer questions based on the following context:

{context_str}

Be concise and factual. If the context doesn't contain relevant information, say so."""

    try:
        stream = await client.chat.completions.create(
            model=settings.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            stream=True
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    except Exception as e:
        logger.error(f"Chat streaming failed: {e}")
        yield f"Error: {str(e)}"


async def synthesize_intelligence(name: str, agent_data: dict) -> dict:
    """
    Final synthesis step: combine all agent findings into coherent intelligence.
    """
    prompt = f"""You are a market intelligence analyst. Synthesize the following agent reports for {name}.

AGENT REPORTS:
{json.dumps(agent_data, indent=2)}

Create a unified analysis. Return JSON:
{{
    "summary": "2-3 sentence executive summary",
    "metrics": {{
        "sentiment": "Bullish" | "Bearish" | "Neutral",
        "signal_strength": 0-100
    }},
    "key_insights": ["insight1", "insight2", "insight3"],
    "risks": ["risk1", "risk2"]
}}
"""

    try:
        response = await client.chat.completions.create(
            model=settings.model_name,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            timeout=60
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Synthesis failed: {e}")
        return {"summary": "Synthesis failed", "error": str(e)}
