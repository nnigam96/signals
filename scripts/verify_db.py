import sys
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def check_db():
    mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/signals")
    
    # Print host only (mask sensitive info)
    if "@" in mongodb_uri:
        host_display = mongodb_uri.split("@")[-1]
    else:
        host_display = mongodb_uri
    print(f"Testing connection to: {host_display}")
    
    try:
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        # The 'ping' command is cheap and fast
        client.admin.command('ping')
        print("SUCCESS: Connected to MongoDB!")
        
        # Check database existence
        db = client.get_default_database()
        print(f"Target Database: {db.name}")
        
    except ConnectionFailure:
        print("ERROR: Connection failed. Check your connection string and IP whitelist.")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    check_db()