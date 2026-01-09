"""
Tools for LangChain Agent - Following Anthropic's Best Practices
Reference: https://www.anthropic.com/engineering/writing-tools-for-agents

Key Principles Applied:
1. Conciseness - Short, clear docstrings
2. Token Efficiency - Minimal, relevant responses
3. Clear Naming - Intuitive, non-overlapping names
4. Meaningful Context - Human-readable but concise
"""

import requests
import json
from datetime import datetime
from typing import Optional
from langchain_core.tools import tool
from config.mongodb import get_conversations_collection, get_preferences_collection, get_mongo_client

# Lazy-load search tool to avoid import errors
_search_tool = None

def _get_search_tool():
    """Lazy initialization of search tool."""
    global _search_tool
    if _search_tool is None:
        try:
            from langchain_community.tools import DuckDuckGoSearchRun
            from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
            _search_tool = DuckDuckGoSearchRun(api_wrapper=DuckDuckGoSearchAPIWrapper())
        except ImportError as e:
            raise ImportError(
                "DuckDuckGo search requires 'ddgs' package. "
                "Install it with: pip install -U ddgs"
            ) from e
    return _search_tool


# ==================== WEB SEARCH TOOLS ====================

@tool
def web_search(query: str) -> str:
    """Search the web for current information. Use for recent events, news, or facts not in training data."""
    try:
        search_tool = _get_search_tool()
        result = search_tool.run(query)
        # Token-efficient: return only essential info, max 500 chars
        return result[:500] if len(result) > 500 else result
    except Exception as e:
        return f"Search error: {str(e)}"


@tool
def weather_search(city: str) -> str:
    """Get current weather for a city. Returns temperature and conditions."""
    try:
        search_tool = _get_search_tool()
        result = search_tool.run(f"current weather {city}")
        # Extract key info, limit to 300 chars for token efficiency
        return result[:300]
    except Exception as e:
        return f"Weather error: {str(e)}"


# ==================== DATABASE TOOLS (Namespaced) ====================

@tool
def db_init() -> str:
    """Initialize MongoDB database connection. Creates collections if they don't exist."""
    try:
        # Test MongoDB connection
        client = get_mongo_client()
        db = client.get_database()
        
        # Create collections (MongoDB creates them automatically on first insert)
        conversations = get_conversations_collection()
        preferences = get_preferences_collection()
        
        # Create indexes for better performance
        conversations.create_index([("user_id", 1), ("timestamp", -1)])
        preferences.create_index([("user_id", 1)], unique=True)
        
        return "MongoDB database ready"
    except Exception as e:
        return f"DB unavailable: {str(e)}"


@tool
def db_save_conversation(user_id: str, message: str, response: str) -> str:
    """Save conversation to MongoDB. Returns 'Saved' on success, or error message if database unavailable."""
    try:
        conversations = get_conversations_collection()
        conversation_doc = {
            "user_id": user_id,
            "message": message,
            "response": response,
            "timestamp": datetime.now().isoformat(),
            "created_at": datetime.now()
        }
        result = conversations.insert_one(conversation_doc)
        if result.inserted_id:
            print(f"✅ Saved conversation for user {user_id}")
            return "Saved"
        else:
            return "Not saved: Insert failed"
    except ConnectionError as e:
        error_msg = f"MongoDB connection error: {str(e)}"
        print(f"❌ {error_msg}")
        return f"Not saved: {error_msg}"
    except Exception as e:
        error_msg = f"Database error: {str(e)}"
        print(f"❌ {error_msg}")
        return f"Not saved: {error_msg}"


@tool
def db_get_history(user_id: str, limit: int = 5) -> str:
    """Get recent conversation history from MongoDB. Returns JSON array or 'No history' if database unavailable."""
    try:
        conversations = get_conversations_collection()
        cursor = conversations.find(
            {"user_id": user_id}
        ).sort("timestamp", -1).limit(limit)
        
        history = []
        for doc in cursor:
            history.append({
                "msg": doc.get("message", "")[:100],
                "resp": doc.get("response", "")[:100],
                "time": doc.get("timestamp", "")
            })
        
        if not history:
            return "No history"
        
        return json.dumps(history)
    except Exception as e:
        return f"No history available: {str(e)}"


@tool
def db_save_preference(user_id: str, preferences: str) -> str:
    """Save user preferences to MongoDB. Returns 'Saved' on success, or error if database unavailable."""
    try:
        preferences_col = get_preferences_collection()
        preference_doc = {
            "user_id": user_id,
            "preferences": preferences,
            "updated_at": datetime.now().isoformat(),
            "last_updated": datetime.now()
        }
        preferences_col.update_one(
            {"user_id": user_id},
            {"$set": preference_doc},
            upsert=True
        )
        return "Saved"
    except Exception as e:
        return f"Not saved: {str(e)}"


# ==================== API TOOLS ====================

@tool
def api_get(url: str, params: Optional[str] = None) -> str:
    """Call GET API endpoint. Returns JSON response. Max 1000 chars."""
    try:
        query_params = json.loads(params) if params else {}
        response = requests.get(url, params=query_params, timeout=10)
        response.raise_for_status()
        result = json.dumps(response.json(), indent=2)
        # Token efficiency: truncate large responses
        return result[:1000] + "..." if len(result) > 1000 else result
    except Exception as e:
        return f"API error: {str(e)}"


@tool
def currency_convert(amount: float, from_curr: str, to_curr: str) -> str:
    """Convert currency using current exchange rates. Returns: amount converted."""
    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{from_curr}"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if to_curr in data.get("rates", {}):
            rate = data["rates"][to_curr]
            converted = amount * rate
            # Concise response: only essential info
            return f"{converted:.2f} {to_curr}"
        return f"Currency {to_curr} not found"
    except Exception as e:
        return f"Conversion error: {str(e)}"


@tool
def get_joke() -> str:
    """Get a random joke. Returns setup and punchline."""
    try:
        response = requests.get("https://official-joke-api.appspot.com/random_joke", 
                              timeout=10)
        data = response.json()
        # Concise format
        return f"{data.get('setup', '')} {data.get('punchline', '')}"
    except Exception as e:
        return f"Joke error: {str(e)}"


# ==================== UTILITY TOOLS ====================

@tool
def calculate(expression: str) -> str:
    """Evaluate math expression. Returns numeric result only."""
    try:
        allowed = set("0123456789+-*/.() ")
        if not all(c in allowed for c in expression):
            return "Invalid expression"
        result = eval(expression)
        # Token-efficient: just the number
        return str(result)
    except Exception as e:
        return f"Calc error: {str(e)}"


@tool
def get_time(timezone: Optional[str] = None) -> str:
    """Get current date and time. Returns: YYYY-MM-DD HH:MM:SS"""
    try:
        now = datetime.now()
        time_str = now.strftime('%Y-%m-%d %H:%M:%S')
        return f"{time_str} {timezone}" if timezone else time_str
    except Exception as e:
        return f"Time error: {str(e)}"


# ==================== EXPORT ====================

def get_all_tools():
    """Return all 11 tools following Anthropic best practices."""
    return [
        web_search,
        weather_search,
        db_init,
        db_save_conversation,
        db_get_history,
        db_save_preference,
        api_get,
        currency_convert,
        get_joke,
        calculate,
        get_time,
    ]
