import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(
    title="Multi-Agent Financial & Web Search API",
    description="AI Agents powered by Groq",
    version="1.0.0"
)

# Allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request body model
class QueryRequest(BaseModel):
    prompt: str

# Import after environment is loaded
from agent.system import MultiAgentSystem

# Instantiate the multi-agent system
agent_system = MultiAgentSystem()

@app.get("/")
async def root():
    return {"message": "Multi-Agent API is running", "status": "active"}

@app.post("/query")
async def handle_query(request: QueryRequest):
    try:
        response = agent_system.query(request.prompt)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}