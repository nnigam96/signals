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


async def calculate_vector_scores(name: str, company_data: dict) -> dict:
    """
    Calculate cross-vector scores for a company based on real data.
    Returns scores (0-100) for: hiring_velocity, product_signals,
    external_attention, funding_activity, and market_momentum.
    """
    # Build context from available company data
    context_parts = []

    if company_data.get("summary"):
        context_parts.append(f"Summary: {company_data['summary']}")

    if company_data.get("metrics"):
        metrics = company_data["metrics"]
        context_parts.append(f"Metrics: sentiment={metrics.get('sentiment')}, signal_strength={metrics.get('signal_strength')}, pmf_score={metrics.get('pmf_score')}")

    if company_data.get("funding"):
        context_parts.append(f"Funding: {company_data['funding']}")

    if company_data.get("strengths"):
        context_parts.append(f"Strengths: {', '.join(company_data['strengths'][:5])}")

    if company_data.get("red_flags"):
        context_parts.append(f"Red flags: {', '.join(company_data['red_flags'][:5])}")

    if company_data.get("competitors"):
        context_parts.append(f"Competitors: {', '.join(company_data['competitors'][:5])}")

    # Include agent findings if available
    if company_data.get("agent_findings"):
        findings = company_data["agent_findings"]
        if findings.get("talent_scout"):
            ts = findings["talent_scout"]
            context_parts.append(f"Hiring data: {ts.get('open_roles', 0)} open roles, departments: {ts.get('departments', [])}")
        if findings.get("tech_auditor"):
            ta = findings["tech_auditor"]
            context_parts.append(f"Tech signals: recent releases={ta.get('recent_releases', [])}, tech stack={ta.get('tech_stack', [])}")
        if findings.get("pricing_analyst"):
            pa = findings["pricing_analyst"]
            context_parts.append(f"Pricing: model={pa.get('pricing_model')}, tiers={pa.get('tiers', [])}")

    # Include raw web/news data snippets
    if company_data.get("raw_context"):
        context_parts.append(f"Additional context: {company_data['raw_context'][:3000]}")

    context = "\n".join(context_parts) if context_parts else "Limited data available."

    prompt = f"""Analyze the following company data for {name} and calculate market intelligence scores.

COMPANY DATA:
{context}

TASK:
Calculate scores (0-100) for each dimension based on the available data:

1. **Hiring Velocity**: Rate of hiring activity, team growth signals, job postings volume
   - High (70-100): Many open roles, aggressive hiring across departments
   - Medium (40-69): Moderate hiring, selective growth
   - Low (0-39): Few/no openings, stable or contracting

2. **Product Signals**: Product development momentum, releases, technical activity
   - High: Frequent releases, active development, expanding features
   - Medium: Steady updates, maintenance mode
   - Low: Stagnant, few updates, technical debt concerns

3. **External Attention**: Market buzz, press coverage, competitive positioning
   - High: Strong media presence, industry recognition, viral growth
   - Medium: Moderate coverage, established presence
   - Low: Under the radar, limited visibility

4. **Funding Activity**: Investment signals, financial health, runway indicators
   - High: Recent funding, strong investor backing, expansion capital
   - Medium: Stable finances, bootstrapped or earlier funding
   - Low: Unknown funding, potential cash concerns

5. **Market Momentum**: Overall market position and growth trajectory (composite)
   - Derived from the above signals plus sentiment and PMF indicators

Return valid JSON only:
{{
    "hiring_velocity": 0-100,
    "product_signals": 0-100,
    "external_attention": 0-100,
    "funding_activity": 0-100,
    "market_momentum": 0-100,
    "reasoning": {{
        "hiring_velocity": "Brief explanation",
        "product_signals": "Brief explanation",
        "external_attention": "Brief explanation",
        "funding_activity": "Brief explanation",
        "market_momentum": "Brief explanation"
    }}
}}
"""

    try:
        response = await client.chat.completions.create(
            model=settings.model_name,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            timeout=60
        )

        content = response.choices[0].message.content
        result = json.loads(content)

        # Ensure all scores are integers in valid range
        for key in ["hiring_velocity", "product_signals", "external_attention", "funding_activity", "market_momentum"]:
            if key in result:
                result[key] = max(0, min(100, int(result[key])))

        result["company"] = name
        return result

    except Exception as e:
        logger.error(f"Vector score calculation failed: {e}")
        return {
            "company": name,
            "hiring_velocity": 50,
            "product_signals": 50,
            "external_attention": 50,
            "funding_activity": 50,
            "market_momentum": 50,
            "reasoning": {"error": str(e)},
            "error": str(e)
        }


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
