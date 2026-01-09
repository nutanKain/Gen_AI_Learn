"""
LangChain Agent with Tools Integration
Following Anthropic's best practices for agent design
"""

from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from config.config import api_key, api_base, api_version, deployment_name
from tools.tools import get_all_tools


def get_llm():
    """
    Initialize and return Azure OpenAI LLM using LangChain
    """
    llm = AzureChatOpenAI(
        azure_endpoint=api_base,
        api_key=api_key,
        api_version=api_version,
        deployment_name=deployment_name,
        temperature=0.7,
    )
    return llm


def get_agent_executor():
    """
    Create an Agent that can use Tools.
    
    Uses LLM with tools bound directly - compatible with all LangChain versions.
    """
    
    # Get the AI brain (LLM)
    llm = get_llm()
    
    # Get all 11 tools
    tools = get_all_tools()
    
    # Create a tool map for easy lookup
    tool_map = {tool.name: tool for tool in tools}
    
    # Bind tools to LLM
    llm_with_tools = llm.bind_tools(tools)
    
    # Create prompt
    system_prompt = """You are a helpful AI assistant with access to tools.

Available tools:
- web_search: Search the internet for current information
- weather_search: Get weather for any city
- db_init: Initialize database (run once)
- db_save_conversation: Save chat to memory
- db_get_history: Retrieve past conversations
- db_save_preference: Save user preferences
- api_get: Call any public API
- currency_convert: Convert between currencies
- get_joke: Get a random joke
- calculate: Do math calculations
- get_time: Get current date/time

When user asks something that needs a tool, USE IT!
For example:
- "What's the weather?" → Use weather_search
- "Search for Python news" → Use web_search
- "Convert 100 USD to EUR" → Use currency_convert
- "What's 25 * 47?" → Use calculate

Always explain what you're doing and use tools when appropriate."""
    
    # Create executor class
    class AgentExecutor:
        def __init__(self, llm, tools, tool_map, system_prompt):
            self.llm = llm
            self.llm_with_tools = llm.bind_tools(tools)
            self.tools = tools
            self.tool_map = tool_map
            self.system_prompt = system_prompt
            self.max_iterations = 10
        
        def invoke(self, input_dict):
            user_input = input_dict.get("input", "")
            messages = [HumanMessage(content=f"{self.system_prompt}\n\nUser: {user_input}")]
            
            iteration = 0
            while iteration < self.max_iterations:
                iteration += 1
                
                # Get LLM response
                response = self.llm_with_tools.invoke(messages)
                messages.append(response)
                
                # Check if tool calls are needed
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    # Execute each tool call
                    for tool_call in response.tool_calls:
                        tool_name = tool_call.get('name', '')
                        tool_args = tool_call.get('args', {})
                        tool_id = tool_call.get('id', '')
                        
                        if tool_name in self.tool_map:
                            try:
                                # Execute the tool
                                tool_result = self.tool_map[tool_name].invoke(tool_args)
                                # Add tool result as ToolMessage
                                messages.append(ToolMessage(
                                    content=str(tool_result),
                                    tool_call_id=tool_id
                                ))
                            except Exception as e:
                                messages.append(ToolMessage(
                                    content=f"Error executing {tool_name}: {str(e)}",
                                    tool_call_id=tool_id
                                ))
                    # Continue loop to get final response
                else:
                    # No more tool calls needed, return the response
                    return {"output": response.content}
            
            # Max iterations reached
            return {"output": "Maximum iterations reached. Please try a simpler question."}
    
    return AgentExecutor(llm, tools, tool_map, system_prompt)


def generate_response(prompt: str, user_id: str = "default", use_memory: bool = True) -> str:
    """
    Generate response using Agent with Tools and Memory.
    
    Args:
        prompt: User's question/request
        user_id: Unique identifier for the user (for memory)
        use_memory: Whether to include conversation history in context
        
    Returns:
        Agent's response after using appropriate tools
    """
    try:
        # Try to initialize database (optional - won't fail if it doesn't work)
        try:
            from tools.tools import db_init
            db_init()
        except:
            pass  # Database is optional, continue without it
        
        # Get conversation history if memory is enabled
        context = ""
        if use_memory:
            try:
                from tools.tools import db_get_history
                import json
                history_str = db_get_history(user_id, limit=3)  # Get last 3 conversations
                if history_str and history_str != "No history" and "error" not in history_str.lower():
                    history = json.loads(history_str)
                    if history:
                        context = "\n\nPrevious conversation context:\n"
                        for conv in reversed(history):  # Oldest first
                            context += f"User: {conv.get('msg', '')}\n"
                            context += f"Assistant: {conv.get('resp', '')}\n"
            except:
                pass  # Continue without history if it fails
        
        # Enhance prompt with context if available
        enhanced_prompt = prompt
        if context:
            enhanced_prompt = f"{context}\n\nCurrent question: {prompt}"
        
        # Get agent executor
        executor = get_agent_executor()
        
        # Run agent with user's question (with context if available)
        result = executor.invoke({
            "input": enhanced_prompt,
            "user_id": user_id
        })
        
        # Get final answer
        response = result.get("output", "Sorry, I couldn't generate a response.")
        
        # ALWAYS save conversation to memory - this is critical!
        save_status = {"saved": False, "error": None}
        try:
            # Import the actual function, not the tool wrapper
            from config.mongodb import get_conversations_collection
            from datetime import datetime
            
            conversations = get_conversations_collection()
            conversation_doc = {
                "user_id": user_id,
                "message": prompt,
                "response": response,
                "timestamp": datetime.now().isoformat(),
                "created_at": datetime.now()
            }
            result = conversations.insert_one(conversation_doc)
            if result.inserted_id:
                save_status = {"saved": True, "error": None}
                print(f"✅ Saved conversation for user {user_id}")
            else:
                save_status = {"saved": False, "error": "Insert failed"}
        except ConnectionError as e:
            save_status = {"saved": False, "error": f"MongoDB connection error: {str(e)}"}
            print(f"❌ {save_status['error']}")
        except Exception as e:
            save_status = {"saved": False, "error": f"Database error: {str(e)}"}
            print(f"❌ {save_status['error']}")
        
        # Store save status in response (will be returned by main.py)
        response_with_status = {
            "content": response,
            "save_status": save_status
        }
        return response_with_status
    except Exception as e:
        return f"Error: {str(e)}"
