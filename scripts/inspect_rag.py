import asyncio
import json
import os
import sys
from typing import List
from dotenv import load_dotenv

# Fix path to import from app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

# Import after path fix
from app.pipeline.mongodb import connect_db, get_knowledge_collection, get_company, list_companies
from app.pipeline.rag import chunk_text, process_and_store_knowledge, embedding_model
from app.pipeline.mongodb import search_knowledge

def test_chunking():
    """Test the text chunking functionality."""
    print("\n=== TESTING CHUNKING ===")
    
    sample_text = """
    This is a test paragraph. It contains some text that will be chunked.
    
    This is another paragraph. It has more content that should be grouped together.
    
    This paragraph is longer and contains more information. It should still be chunked appropriately based on the chunk size limit. The chunking algorithm splits by paragraphs first, then combines them if they fit within the size limit.
    
    Short paragraph.
    
    Another longer paragraph with more details. This helps test how the chunking handles varying paragraph sizes and ensures that the algorithm works correctly for different types of content.
    """
    
    chunks = chunk_text(sample_text, chunk_size=200)
    
    print(f"Original text length: {len(sample_text)} chars")
    print(f"Number of chunks: {len(chunks)}")
    print("\nChunks:")
    for i, chunk in enumerate(chunks, 1):
        print(f"\n  Chunk {i} ({len(chunk)} chars):")
        print(f"    {chunk[:150]}...")
    
    return chunks

def test_embedding(chunks: List[str]):
    """Test the embedding generation."""
    print("\n=== TESTING EMBEDDING ===")
    
    if not chunks:
        print("No chunks to embed")
        return None
    
    print(f"Generating embeddings for {len(chunks)} chunks...")
    embeddings_generator = embedding_model.embed(chunks)
    vectors = [v.tolist() for v in embeddings_generator]
    
    print(f"Generated {len(vectors)} embeddings")
    if vectors:
        print(f"Vector dimension: {len(vectors[0])}")
        print(f"First vector sample (first 10 values): {vectors[0][:10]}")
    
    return vectors

async def test_store_knowledge():
    """Test storing knowledge in MongoDB."""
    print("\n=== TESTING STORE KNOWLEDGE ===")
    
    connect_db()
    
    test_slug = "test-company"
    test_text = """
    Test Company is a leading provider of AI solutions.
    They specialize in natural language processing and machine learning.
    Founded in 2020, the company has raised $50M in funding.
    Their main product is an AI assistant that helps with customer service.
    The company has offices in San Francisco and New York.
    They serve over 1000 customers worldwide.
    """
    
    print(f"Storing knowledge for slug: {test_slug}")
    print(f"Text length: {len(test_text)} chars")
    
    await process_and_store_knowledge(test_slug, test_text, "test")
    
    # Verify it was stored
    coll = get_knowledge_collection()
    stored = list(coll.find({"company_slug": test_slug, "source": "test"}))
    print(f"Stored {len(stored)} chunks")
    
    return test_slug

async def test_search_knowledge(query: str, company_slug: str = None):
    """Test searching the knowledge base."""
    print(f"\n=== TESTING SEARCH KNOWLEDGE ===")
    print(f"Query: {query}")
    if company_slug:
        print(f"Filtered to company: {company_slug}")
    
    try:
        results = search_knowledge(query, company_slug=company_slug, limit=5)
        print(f"Found {len(results)} results")
        
        for i, result in enumerate(results, 1):
            score = result.get("score", 0)
            source = result.get("source", "unknown")
            text = result.get("text", "")
            print(f"\n  Result {i} (score: {score:.4f}, source: {source}):")
            print(f"    {text[:200]}...")
        
        return results
    except Exception as e:
        print(f"Search error: {e}")
        print("Note: Vector search requires MongoDB Atlas with vector search index configured")
        return []

async def show_knowledge_stats():
    """Show statistics about stored knowledge."""
    print("\n=== KNOWLEDGE BASE STATISTICS ===")
    
    connect_db()
    coll = get_knowledge_collection()
    
    # Total chunks
    total_chunks = coll.count_documents({})
    print(f"Total chunks stored: {total_chunks}")
    
    if total_chunks == 0:
        print("No knowledge stored yet. Run the pipeline to store some data.")
        return
    
    # Group by company
    pipeline = [
        {"$group": {
            "_id": "$company_slug",
            "count": {"$sum": 1},
            "sources": {"$addToSet": "$source"}
        }},
        {"$sort": {"count": -1}}
    ]
    
    company_stats = list(coll.aggregate(pipeline))
    print(f"\nCompanies in knowledge base: {len(company_stats)}")
    
    for stat in company_stats[:10]:  # Show top 10
        slug = stat["_id"]
        count = stat["count"]
        sources = stat["sources"]
        print(f"  {slug}: {count} chunks from {sources}")
    
    # Group by source
    source_pipeline = [
        {"$group": {
            "_id": "$source",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}}
    ]
    
    source_stats = list(coll.aggregate(source_pipeline))
    print(f"\nSources breakdown:")
    for stat in source_stats:
        source = stat["_id"]
        count = stat["count"]
        print(f"  {source}: {count} chunks")

async def test_full_rag_workflow():
    """Test the full RAG workflow with a real company."""
    print("\n=== TESTING FULL RAG WORKFLOW ===")
    
    # Get a company from the database
    companies = list_companies()
    if not companies:
        print("No companies found in database. Run the pipeline first to create some companies.")
        return
    
    company = companies[0]
    slug = company.get("slug")
    name = company.get("name", slug)
    
    print(f"Testing with company: {name} (slug: {slug})")
    
    # Check if knowledge exists
    coll = get_knowledge_collection()
    existing = list(coll.find({"company_slug": slug}).limit(1))
    
    if not existing:
        print(f"No knowledge stored for {name}. The RAG system needs data from the pipeline.")
        print("Knowledge is automatically stored when you run the pipeline.")
        return
    
    # Test queries
    test_queries = [
        f"What is {name}?",
        f"What does {name} do?",
        f"Tell me about {name}'s products",
    ]
    
    for query in test_queries:
        print(f"\n--- Query: {query} ---")
        results = await test_search_knowledge(query, company_slug=slug)
        if results:
            print(f"Found relevant context with {len(results)} chunks")

async def main():
    print("RAG System Inspector")
    print("=" * 50)
    
    # Test 1: Chunking
    chunks = test_chunking()
    
    # Test 2: Embedding
    vectors = test_embedding(chunks)
    
    # Test 3: Connect to DB
    print("\n=== CONNECTING TO DATABASE ===")
    try:
        connect_db()
        print("Connected to MongoDB")
    except Exception as e:
        print(f"Database connection error: {e}")
        print("Make sure MongoDB is running and MONGODB_URI is set in .env")
        return
    
    # Test 4: Store knowledge (optional test)
    if len(sys.argv) > 1 and sys.argv[1] == "--store-test":
        await test_store_knowledge()
    
    # Test 5: Show statistics
    await show_knowledge_stats()
    
    # Test 6: Search knowledge
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        if query != "--store-test":
            await test_search_knowledge(query)
    else:
        # Test with a default query
        await test_search_knowledge("AI company")
    
    # Test 7: Full workflow
    await test_full_rag_workflow()
    
    print("\n" + "=" * 50)
    print("Inspection complete!")

if __name__ == "__main__":
    asyncio.run(main())