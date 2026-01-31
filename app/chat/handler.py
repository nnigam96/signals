import logging
from typing import AsyncGenerator, Any
from app.pipeline.mongodb import search_companies, list_companies
from app.pipeline.openrouter import chat_with_context
from app.pipeline.orchestrator import run_pipeline

logger = logging.getLogger(__name__)

async def handle_chat_message(message: str) -> AsyncGenerator[dict[str, Any], None]:
    # 1. Simple intent detection
    lower = message.lower()
    trigger_words = ["analyze", "research", "deep dive", "look up"]
    is_analyze = any(w in lower for w in trigger_words)
    
    # 2. Extract potential company name (naïve approach: look for Capitalized Words)
    # For hackathon, assume the last capitalized word or the whole query if short
    query = message.replace("Analyze", "").strip()

    # 3. Check DB first
    existing = search_companies(query)
    
    if existing and not is_analyze:
        yield {"type": "text", "content": f"Found info on **{existing[0]['name']}**.\n\n"}
        async for chunk in chat_with_context(message, existing):
            yield {"type": "text", "content": chunk}
        yield {"type": "companies", "content": existing}
        yield {"type": "done"}
        return

    # 4. If not found or explicitly asked to analyze -> Run Pipeline
    if is_analyze or (len(query.split()) < 4 and not existing):
        yield {"type": "text", "content": f"🔍 Searching for **{query}**...\n"}
        
        try:
            # Run the heavy pipeline
            profile = await run_pipeline(name=query)
            
            yield {"type": "text", "content": "✅ Data acquired. Analyzing...\n\n"}
            async for chunk in chat_with_context("Summarize this company", [profile]):
                yield {"type": "text", "content": chunk}
            
            yield {"type": "companies", "content": [profile]}
        except Exception as e:
            yield {"type": "text", "content": f"❌ Error: {str(e)}"}
            
        yield {"type": "done"}
        return

    # 5. General chat
    all_context = list_companies()
    async for chunk in chat_with_context(message, all_context):
        yield {"type": "text", "content": chunk}
    yield {"type": "done"}