import asyncio
import httpx
import json
import sys

# Configuration
API_URL = "http://localhost:3001/api/chat"  # Change port to 3001 if using that
TEST_COMPANY = "Linear"  # A good target with clear pricing/careers pages

async def send_message(message: str):
    print(f"\n🔵 USER: {message}")
    print("-------------------------------------------------")
    
    async with httpx.AsyncClient(timeout=120) as client:
        # Your API expects a POST with JSON body
        # and returns a Server-Sent Events (SSE) stream
        async with client.stream("POST", API_URL, json={"message": message}) as response:
            if response.status_code != 200:
                print(f"❌ Error {response.status_code}: {await response.aread()}")
                return

            # Read the stream line by line
            async for line in response.aiter_lines():
                if not line:
                    continue
                
                # SSE lines usually start with "data: "
                if line.startswith("data: "):
                    raw_json = line[6:]  # Strip "data: " prefix
                    
                    try:
                        data = json.loads(raw_json)
                        
                        # Handle different event types from your Chat Handler
                        if data.get("type") == "text":
                            # Print text chunks without newlines for a streaming effect
                            sys.stdout.write(data.get("content", ""))
                            sys.stdout.flush()
                            
                        elif data.get("type") == "companies":
                            print(f"\n\n[📦 DATA RECEIVED: Company Card for {data['content'][0].get('name')}]")
                            
                        elif data.get("type") == "error":
                            print(f"\n❌ API Error: {data.get('content')}")
                            
                        elif data.get("type") == "done":
                            print("\n\n[✅ Stream Complete]")
                            
                    except json.JSONDecodeError:
                        print(f"⚠️  Decode Error: {line}")
    print("\n-------------------------------------------------")

async def main():
    # TEST 1: The "Write" Path (Ingestion)
    # This forces the backend to Crawl -> Agent -> Embed -> Store
    print(f"🚀 TEST 1: Ingesting '{TEST_COMPANY}' via API...")
    await send_message(f"Analyze {TEST_COMPANY}")

    # Pause to let you read/verify
    input("\n⏸️  Ingestion complete. Press Enter to test RAG Retrieval...")

    # TEST 2: The "Read" Path (RAG Retrieval)
    # This verifies the Vector Search is actually working
    print(f"🧠 TEST 2: Querying RAG for '{TEST_COMPANY}'...")
    # Asking a specific question forces it to look up the "Knowledge" collection
    await send_message(f"What is the pricing model for {TEST_COMPANY}?")

if __name__ == "__main__":
    asyncio.run(main())