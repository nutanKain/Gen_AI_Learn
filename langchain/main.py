"""
FastAPI application entry point with Agent Tools
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from agent import generate_response

app = FastAPI(
    title="LangChain Chatbot with Tools",
    description="A chatbot with 11 tools: web search, database, API calls, and utilities",
    version="1.0.0"
)


class PromptRequest(BaseModel):
    prompt: str
    user_id: str = "default"


@app.get("/")
def read_root():
    return {
        "message": "LangChain FastAPI Application with Tools",
        "tools_count": 11,
        "features": [
            "Web Search (2 tools)",
            "Database Operations (4 tools)",
            "API Calls (3 tools)",
            "Utilities (2 tools)"
        ],
        "docs": "/docs"
    }


@app.get("/generate")
def generate_get(
    prompt: str = Query(..., description="The question or prompt for the chatbot"),
    user_id: str = Query("default", description="User identifier for conversation memory")
):
    """
    Generate a response using LangChain Agent with Tools (GET method).
    
    Use this endpoint in your browser or with simple GET requests.
    
    Example: http://127.0.0.1:8000/generate?prompt=What's%20the%20weather%20in%20London?
    
    The agent will automatically use appropriate tools based on your question.
    """
    try:
        result = generate_response(prompt, user_id)
        
        # Handle new response format with save_status
        if isinstance(result, dict) and "content" in result:
            response_text = result["content"]
            save_status = result.get("save_status", {"saved": False, "error": "Unknown"})
        else:
            # Fallback for old format
            response_text = result
            save_status = {"saved": False, "error": "Status not available"}
        
        return {
            "response": response_text,
            "user_id": user_id,
            "status": "success",
            "saved_to_memory": save_status.get("saved", False),
            "save_error": save_status.get("error"),
            "message": "Conversation saved to MongoDB" if save_status.get("saved") else f"Save failed: {save_status.get('error', 'Unknown error')}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate")
def generate_post(request: PromptRequest):
    """
    Generate a response using LangChain Agent with Tools (POST method).
    
    The agent will automatically use appropriate tools based on your question.
    
    Examples:
    - "What's the weather in London?" → Uses weather_search tool
    - "Convert 100 USD to EUR" → Uses currency_convert tool
    - "Search for Python news" → Uses web_search tool
    - "What's 25 * 47?" → Uses calculate tool
    
    Args:
        request: Request body containing prompt and optional user_id
        
    Returns:
        The generated response from the agent
    """
    try:
        result = generate_response(request.prompt, request.user_id)
        
        # Handle new response format with save_status
        if isinstance(result, dict) and "content" in result:
            response_text = result["content"]
            save_status = result.get("save_status", {"saved": False, "error": "Unknown"})
        else:
            # Fallback for old format
            response_text = result
            save_status = {"saved": False, "error": "Status not available"}
        
        return {
            "response": response_text,
            "user_id": request.user_id,
            "status": "success",
            "saved_to_memory": save_status.get("saved", False),
            "save_error": save_status.get("error"),
            "message": "Conversation saved to MongoDB" if save_status.get("saved") else f"Save failed: {save_status.get('error', 'Unknown error')}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools")
def list_tools():
    """
    List all available tools with descriptions.
    """
    from tools.tools import get_all_tools
    tools = get_all_tools()
    return {
        "total_tools": len(tools),
        "tools": [
            {
                "name": tool.name,
                "description": tool.description
            }
            for tool in tools
        ]
    }


@app.get("/memory/history")
def get_conversation_history(
    user_id: str = Query("default", description="User identifier"),
    limit: int = Query(10, description="Number of recent conversations to retrieve")
):
    """
    Get conversation history for a user from database memory.
    
    Example: http://127.0.0.1:8000/memory/history?user_id=myuser&limit=5
    """
    try:
        from tools.tools import db_get_history
        import json
        history_str = db_get_history(user_id, limit)
        
        if history_str == "No history" or "error" in history_str.lower():
            return {
                "user_id": user_id,
                "history": [],
                "message": history_str
            }
        
        history = json.loads(history_str)
        return {
            "user_id": user_id,
            "count": len(history),
            "history": history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory/preferences")
def get_user_preferences(
    user_id: str = Query("default", description="User identifier")
):
    """
    Get user preferences from database memory.
    
    Example: http://127.0.0.1:8000/memory/preferences?user_id=myuser
    """
    try:
        import json
        from config.mongodb import get_preferences_collection
        
        preferences_col = get_preferences_collection()
        doc = preferences_col.find_one({"user_id": user_id})
        
        if doc:
            return {
                "user_id": user_id,
                "preferences": json.loads(doc.get("preferences", "{}")) if doc.get("preferences") else {},
                "updated_at": doc.get("updated_at", "")
            }
        else:
            return {
                "user_id": user_id,
                "preferences": {},
                "message": "No preferences found"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memory/preferences")
def save_user_preferences(
    user_id: str = Query(..., description="User identifier"),
    preferences: str = Query(..., description="JSON string of preferences")
):
    """
    Save user preferences to database memory.
    
    Example: POST /memory/preferences?user_id=myuser&preferences={"temperature_unit":"celsius"}
    """
    try:
        from tools.tools import db_save_preference
        result = db_save_preference(user_id, preferences)
        return {
            "user_id": user_id,
            "status": result,
            "preferences": preferences
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory/verify")
def verify_saved_conversations(
    user_id: str = Query("default", description="User identifier")
):
    """
    Verify that conversations are being saved.
    Shows count of saved conversations for a user.
    
    Example: http://127.0.0.1:8000/memory/verify?user_id=myuser
    """
    try:
        from config.mongodb import get_conversations_collection
        
        conversations = get_conversations_collection()
        count = conversations.count_documents({"user_id": user_id})
        
        # Get latest conversation
        latest = conversations.find_one(
            {"user_id": user_id},
            sort=[("timestamp", -1)]
        )
        
        return {
            "user_id": user_id,
            "total_conversations_saved": count,
            "latest_conversation": {
                "message": latest.get("message", "") if latest else None,
                "response": latest.get("response", "")[:100] + "..." if latest and latest.get("response") else None,
                "timestamp": latest.get("timestamp", "") if latest else None
            } if latest else None,
            "status": "active" if count > 0 else "no_conversations_yet",
            "message": f"Found {count} saved conversation(s) for this user"
        }
    except Exception as e:
        return {
            "user_id": user_id,
            "error": str(e),
            "status": "error"
        }


@app.get("/memory/check-db")
def check_database_connection():
    """
    Check if MongoDB connection is working.
    
    Example: http://127.0.0.1:8000/memory/check-db
    """
    try:
        from config.mongodb import get_mongo_client, DATABASE_NAME, MONGODB_URI
        from config.mongodb import get_conversations_collection
        
        # Test connection
        client = get_mongo_client()
        db_info = client.server_info()
        
        # Test collection access
        conversations = get_conversations_collection()
        count = conversations.count_documents({})
        
        return {
            "status": "connected",
            "mongodb_uri": MONGODB_URI,
            "database_name": DATABASE_NAME,
            "server_version": db_info.get("version", "unknown"),
            "total_conversations": count,
            "message": "MongoDB connection is working!"
        }
    except ConnectionError as e:
        return {
            "status": "not_connected",
            "error": str(e),
            "message": "MongoDB connection failed. Make sure MongoDB is running.",
            "help": {
                "local_mongodb": "Install and start MongoDB: https://www.mongodb.com/try/download/community",
                "mongodb_atlas": "Get free MongoDB Atlas: https://www.mongodb.com/cloud/atlas",
                "env_file": "Add MONGODB_URI to your .env file"
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Error checking database connection"
        }


@app.get("/memory/demo")
def memory_demo():
    """
    Demo endpoint that creates REAL conversations using the LLM to show how memory works.
    
    This will:
    1. Create a test user
    2. Have 3 REAL conversations with the LLM (weather, name, etc.)
    3. Show the conversation history
    
    Example: http://127.0.0.1:8000/memory/demo
    """
    try:
        import json
        from tools.tools import db_init, db_get_history
        
        # Initialize database
        db_init_result = db_init()
        
        demo_user_id = "demo_user_123"
        
        # REAL conversation prompts - will get actual LLM responses
        prompts = [
            "My name is Alice and I love Python programming",
            "What's the weather in London?",  # Real tool usage
            "What's my name?"  # Tests memory
        ]
        
        results = []
        
        # Have REAL conversations with the LLM
        for i, prompt in enumerate(prompts, 1):
            try:
                # Generate REAL response using LLM and tools
                response = generate_response(prompt, demo_user_id)
                
                # Extract response text
                if isinstance(response, dict) and "content" in response:
                    response_text = response["content"]
                    save_status = response.get("save_status", {})
                else:
                    response_text = response
                    save_status = {}
                
                results.append({
                    "conversation": i,
                    "user": prompt,
                    "bot": response_text,
                    "saved": "Yes" if save_status.get("saved") else f"No: {save_status.get('error', 'Unknown')}"
                })
            except Exception as e:
                results.append({
                    "conversation": i,
                    "user": prompt,
                    "bot": f"Error: {str(e)}",
                    "saved": "No"
                })
        
        # Get history
        try:
            history_str = db_get_history(demo_user_id, limit=5)
            if history_str and history_str != "No history" and "error" not in history_str.lower():
                history = json.loads(history_str)
            else:
                history = []
        except:
            history = []
        
        return {
            "message": "Real demo conversations created with LLM!",
            "database_status": db_init_result,
            "user_id": demo_user_id,
            "conversations_created": len(prompts),
            "conversations": results,
            "stored_history": history,
            "history_count": len(history),
            "note": "All conversations used REAL LLM responses and tools (like weather_search)",
            "how_to_test": {
                "step_1": f"View history: http://127.0.0.1:8000/memory/history?user_id={demo_user_id}",
                "step_2": f"Ask follow-up: http://127.0.0.1:8000/generate?prompt=What%27s%20my%20name%3F&user_id={demo_user_id}",
                "step_3": "The bot should remember your name from previous conversations!"
            }
        }
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "message": "There was an error creating the demo. Check if MongoDB and LLM are working."
        }


@app.get("/memory/test")
def test_memory_flow():
    """
    Interactive test flow for memory - shows step-by-step how memory works.
    
    Example: http://127.0.0.1:8000/memory/test
    """
    try:
        demo_user_id = "test_user_456"
        
        return {
            "message": "Memory Test Flow - Follow these steps:",
            "user_id": demo_user_id,
            "steps": [
                {
                    "step": 1,
                    "action": "Tell the bot your name",
                    "url": f"/generate?prompt=My%20name%20is%20Bob&user_id={demo_user_id}",
                    "description": "This saves your name to memory"
                },
                {
                    "step": 2,
                    "action": "Ask the bot your name",
                    "url": f"/generate?prompt=What%27s%20my%20name%3F&user_id={demo_user_id}",
                    "description": "Bot should remember from step 1"
                },
                {
                    "step": 3,
                    "action": "View conversation history",
                    "url": f"/memory/history?user_id={demo_user_id}&limit=5",
                    "description": "See all saved conversations"
                },
                {
                    "step": 4,
                    "action": "Have another conversation",
                    "url": f"/generate?prompt=I%20like%20pizza&user_id={demo_user_id}",
                    "description": "More conversations = more memory"
                },
                {
                    "step": 5,
                    "action": "Ask about previous conversation",
                    "url": f"/generate?prompt=What%20do%20I%20like%3F&user_id={demo_user_id}",
                    "description": "Bot uses memory to answer"
                }
            ],
            "note": "Use the same user_id in all requests to maintain memory!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
