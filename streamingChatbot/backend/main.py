from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from agent.agent import chatbot

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/chat")   
async def chat(request: Request, prompt: str):
    """
    Generate a chat response for the given prompt.
    SSE Endpoint
    Eg - http://localhost:8000/chat?prompt=Hello
    """  

    return StreamingResponse(chatbot(prompt,request),
    media_type="text/event-stream",
    headers={
        "Cache-Control":"no-cache",
        "Connection":"keep-alive",
        "X-Accel-Buffering": "no",
    }    
    )