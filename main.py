import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backtest_engine import run_ma_crossover_backtest
from ai_signal import extract_ai_signal

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

class BacktestRequest(BaseModel):
    symbol: str
    fast_window: int = 10
    slow_window: int = 30
    start_date: str | None = None
    end_date: str | None = None

class AISignalRequest(BaseModel):
    symbol: str
    
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

@app.post("/backtest")
async def handle_backtest(request: BacktestRequest):
    try:
        result = run_ma_crossover_backtest(
            symbol=request.symbol,
            fast_window=request.fast_window,
            slow_window=request.slow_window,
            start_date=request.start_date,
            end_date=request.end_date,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai-signal")
async def handle_ai_signal(request: AISignalRequest):
    try:
        result = extract_ai_signal(request.symbol)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}