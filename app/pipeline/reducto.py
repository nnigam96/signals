import logging
from typing import Any
import httpx
from app.config import settings

logger = logging.getLogger(__name__)
REDUCTO_BASE = "https://platform.reducto.ai"

async def parse_document(input_data: str) -> dict[str, Any]:
    logger.info("[reducto] Parsing document...")
    is_url = input_data.startswith("http")
    body = {"document_url": input_data} if is_url else {"document_url": f"data:application/pdf;base64,{input_data}"}

    async with httpx.AsyncClient(timeout=60) as client:
        res = await client.post(
            f"{REDUCTO_BASE}/parse",
            headers={"Authorization": f"Bearer {settings.reducto_api_key}"},
            json=body,
        )

    if res.status_code != 200:
        raise RuntimeError(f"Reducto failed: {res.text[:200]}")

    data = res.json()
    # Flatten text for the LLM
    full_text = ""
    if "result" in data:
        blocks = data["result"].get("blocks", [])
        full_text = "\n".join([b.get("content", "") for b in blocks])
    
    return {
        "extracted_text": full_text,
        "raw": data
    }