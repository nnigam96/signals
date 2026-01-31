import logging
import asyncio
from typing import List
from fastembed import TextEmbedding

logger = logging.getLogger(__name__)

# Initialize model once (downloads ~250MB on first run)
# We use BAAI/bge-small-en-v1.5 which is very efficient
logger.info("[rag] Loading embedding model...")
embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

def chunk_text(text: str, chunk_size: int = 500) -> List[str]:
    """Splits text into manageably sized chunks for embedding."""
    if not text: return []
    
    # Simple split by paragraphs first
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""
    
    for p in paragraphs:
        # If adding the next paragraph keeps us under limit, add it
        if len(current_chunk) + len(p) < chunk_size:
            current_chunk += p + "\n\n"
        else:
            # Otherwise, seal this chunk and start a new one
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            current_chunk = p + "\n\n"
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks

async def process_and_store_knowledge(slug: str, text: str, source_type: str):
    """
    1. Chunks the text.
    2. Embeds it into vectors.
    3. Stores it in MongoDB 'knowledge' collection.
    """
    from app.pipeline.mongodb import get_knowledge_collection
    
    if not text: return

    logger.info(f"[rag] Processing {len(text)} chars from {source_type} for {slug}...")
    
    # 1. Chunking
    # Run in executor to avoid blocking the event loop
    loop = asyncio.get_running_loop()
    chunks = await loop.run_in_executor(None, chunk_text, text)
    
    if not chunks: return

    # 2. Embedding
    # fastembed is fast, but better to treat as blocking I/O
    embeddings_generator = embedding_model.embed(chunks)
    vectors = [v.tolist() for v in embeddings_generator] # Convert numpy to list

    # 3. Storage
    docs = []
    for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
        docs.append({
            "company_slug": slug,
            "text": chunk,
            "vector": vector,
            "source": source_type,
            "chunk_index": i
        })
    
    coll = get_knowledge_collection()
    if docs:
        # Delete old knowledge for this source to prevent duplicates
        await coll.delete_many({"company_slug": slug, "source": source_type})
        await coll.insert_many(docs)
        logger.info(f"[rag] ✅ Stored {len(docs)} chunks for {slug}")