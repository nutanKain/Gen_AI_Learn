"""
MongoDB connection configuration
"""
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from typing import Optional

load_dotenv(override=True)

# MongoDB connection string from environment variable
# Default: mongodb://localhost:27017 (local MongoDB)
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("MONGODB_DATABASE", "chatbot_db")

# Global MongoDB client (singleton)
_mongo_client: Optional[MongoClient] = None
_db = None


def get_mongo_client():
    """Get or create MongoDB client connection."""
    global _mongo_client
    if _mongo_client is None:
        try:
            _mongo_client = MongoClient(
                MONGODB_URI, 
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=5000
            )
            # Test connection
            _mongo_client.server_info()
            print(f"✅ Connected to MongoDB: {DATABASE_NAME}")
        except Exception as e:
            error_msg = f"Failed to connect to MongoDB at {MONGODB_URI}: {str(e)}"
            print(f"❌ {error_msg}")
            print(f"💡 Make sure MongoDB is running or check MONGODB_URI in .env file")
            raise ConnectionError(error_msg)
    return _mongo_client


def get_database():
    """Get database instance."""
    global _db
    if _db is None:
        client = get_mongo_client()
        _db = client[DATABASE_NAME]
    return _db


def get_conversations_collection():
    """Get conversations collection."""
    db = get_database()
    return db["conversations"]


def get_preferences_collection():
    """Get user preferences collection."""
    db = get_database()
    return db["user_preferences"]
