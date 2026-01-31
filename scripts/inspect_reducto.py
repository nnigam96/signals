import asyncio
import json
import os
import sys
import httpx
from dotenv import load_dotenv

# Fix path to import from app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

REDUCTO_API_KEY = os.getenv("REDUCTO_API_KEY")
# [Corrected] The valid base URL is platform.reducto.ai
BASE_URL = "https://platform.reducto.ai"

async def inspect_pdf(pdf_path):
    if not os.path.exists(pdf_path):
        print(f"❌ File not found: {pdf_path}")
        return

    headers = {"Authorization": f"Bearer {REDUCTO_API_KEY}"}

    async with httpx.AsyncClient(timeout=120) as client:
        # STEP 1: Upload the document
        print(f"PAGE 1: Uploading {pdf_path}...")
        
        # Use multipart/form-data for the file
        with open(pdf_path, "rb") as f:
            files = {"file": (os.path.basename(pdf_path), f, "application/pdf")}
            upload_res = await client.post(
                f"{BASE_URL}/upload", 
                headers=headers, 
                files=files
            )
        
        if upload_res.status_code != 200:
            print(f"❌ Upload Error {upload_res.status_code}: {upload_res.text}")
            return
        
        # Extract file_id (usually starts with "reducto://")
        upload_data = upload_res.json()
        file_id = upload_data.get("file_id")
        print(f"✅ Uploaded. ID: {file_id}")

        # STEP 2: Parse the document
        print("PAGE 2: Parsing document...")
        
        # Use the /parse endpoint with the file_id in 'document_url'
        parse_payload = {
            "document_url": file_id,
        }
        
        res = await client.post(
            f"{BASE_URL}/parse",
            headers=headers,
            json=parse_payload
        )

    if res.status_code != 200:
        print(f"❌ Parse Error {res.status_code}: {res.text}")
        return

    data = res.json()
    
    # Save the RAW JSON
    output_file = "reducto_debug.json"
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"\n✅ Raw data saved to: {output_file}")
    
    # Reducto returns a list of 'chunks' in the 'result' object
    result = data.get("result", {})
    chunks = result.get("chunks", []) if isinstance(result, dict) else []
    
    # Flatten blocks
    all_blocks = []
    for chunk in chunks:
        all_blocks.extend(chunk.get("blocks", []))

    tables = [b for b in all_blocks if b.get("type") == "Table"]
    
    print("\n--- SUMMARY ---")
    print(f"Total Chunks:    {len(chunks)}")
    print(f"Total Blocks:    {len(all_blocks)}")
    print(f"Tables Found:    {len(tables)}")
    
    if all_blocks:
        first_content = all_blocks[0].get('content') or all_blocks[0].get('text', '')
        print(f"First block:     {str(first_content)[:100]}...")
    print("-" * 30)

if __name__ == "__main__":
    # Ensure this path is correct on your machine
    target_pdf = "test_data/doordash-230217170346-5041f3d8.pdf" 
    
    if len(sys.argv) > 1:
        target_pdf = sys.argv[1]
        
    asyncio.run(inspect_pdf(target_pdf))