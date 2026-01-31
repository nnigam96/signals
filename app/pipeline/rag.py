import logging
import asyncio
from typing import List

from fastembed import TextEmbedding

from app.config import settings

logger = logging.getLogger(__name__)

# Initialize embedding model once (downloads ~250MB on first run)
logger.info("[rag] Loading embedding model...")
embedding_model = TextEmbedding(model_name=settings.embedding_model)


def chunk_text(text: str, chunk_size: int = 500) -> List[str]:
    """Splits text into manageably sized chunks for embedding."""
    if not text:
        return []

    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""

    for p in paragraphs:
        if len(current_chunk) + len(p) < chunk_size:
            current_chunk += p + "\n\n"
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            current_chunk = p + "\n\n"

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for a list of texts."""
    if not texts:
        return []
    embeddings_generator = embedding_model.embed(texts)
    return [v.tolist() for v in embeddings_generator]


def embed_query(query: str) -> List[float]:
    """Generate embedding for a single query."""
    return list(embedding_model.embed([query]))[0].tolist()


async def process_and_store_knowledge(slug: str, text: str, source_type: str):
    """
    1. Chunks the text.
    2. Embeds it into vectors.
    3. Stores it in MongoDB 'knowledge' collection.
    """
    from app.pipeline.mongodb import get_knowledge_collection, delete_knowledge

    if not text:
        return

    logger.info(f"[rag] Processing {len(text)} chars from {source_type} for {slug}...")

    # 1. Chunking (run in executor to avoid blocking)
    loop = asyncio.get_running_loop()
    chunks = await loop.run_in_executor(None, chunk_text, text)

    if not chunks:
        return

    # 2. Embedding (run in executor - CPU intensive)
    vectors = await loop.run_in_executor(None, embed_texts, chunks)

    # 3. Prepare documents
    docs = []
    for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
        docs.append({
            "company_slug": slug,
            "text": chunk,
            "vector": vector,
            "source": source_type,
            "chunk_index": i
        })

    # 4. Store in MongoDB (synchronous operations wrapped for async context)
    coll = get_knowledge_collection()
    if docs:
        # Delete old knowledge for this source to prevent duplicates
        await loop.run_in_executor(None, lambda: coll.delete_many({"company_slug": slug, "source": source_type}))
        await loop.run_in_executor(None, lambda: coll.insert_many(docs))
        logger.info(f"[rag] Stored {len(docs)} chunks for {slug}")


def process_and_store_knowledge_sync(slug: str, text: str, source_type: str):
    """
    Synchronous version of process_and_store_knowledge for non-async contexts.
    """
    from app.pipeline.mongodb import get_knowledge_collection

    if not text:
        return

    logger.info(f"[rag] Processing {len(text)} chars from {source_type} for {slug}...")

    # 1. Chunking
    chunks = chunk_text(text)
    if not chunks:
        return

    # 2. Embedding
    vectors = embed_texts(chunks)

    # 3. Prepare documents
    docs = []
    for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
        docs.append({
            "company_slug": slug,
            "text": chunk,
            "vector": vector,
            "source": source_type,
            "chunk_index": i
        })

    # 4. Store in MongoDB
    coll = get_knowledge_collection()
    if docs:
        coll.delete_many({"company_slug": slug, "source": source_type})
        coll.insert_many(docs)
        logger.info(f"[rag] Stored {len(docs)} chunks for {slug}")
