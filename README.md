
# 📈 FinaAgent — AI-Powered Financial Analysis Platform

> A multi-agent financial intelligence system that combines real-time market data, SEC 10-K document analysis, AI-driven trading signals, and backtesting — all in an interactive Streamlit dashboard.

---

## 🧠 Overview

**FinaAgent** is a full-stack AI financial analysis platform built with a **FastAPI backend** and a **Streamlit frontend**. It leverages a **multi-agent architecture** powered by **Groq LLMs (Llama 3.3-70B)** to answer financial questions, extract sentiment signals from SEC filings, and run quantitative backtests.

### Key Capabilities

| Feature | Description |
|---|---|
| 💬 **AI Chat** | Natural-language financial Q&A via the Finance & Web Search agents |
| 📊 **Stock Dashboard** | Real-time price charts, fundamentals, and key metrics via yFinance |
| 🤖 **AI Signal Extraction** | Sentiment & hedging analysis from SEC 10-K filings using Groq LLM |
| 📉 **Backtesting Engine** | MA-crossover strategy with AI signal filtering and ablation testing |
| 🔍 **Observability** | Full LLM trace logging via Langfuse |

---

## 🏗️ Architecture

```
FinaAgent/
├── main.py                  # FastAPI backend (REST API)
├── app.py                   # Streamlit frontend (UI)
├── agent/
│   ├── system.py            # Multi-agent router
│   ├── finance.py           # Finance Agent (stock data + LLM)
│   ├── search.py            # Web Search Agent
│   └── base.py              # BaseAgent class
├── ai_signal.py             # SEC 10-K extraction + Groq LLM sentiment
├── backtest_engine.py       # MA-crossover backtesting + ablation
├── data_fetcher.py          # Cached yFinance data gateway
├── stock_dashboard.py       # Streamlit stock dashboard components
├── cache_manager.py         # In-memory caching layer
├── observability.py         # Langfuse tracing & structured logging
├── news_fetcher.py          # Financial news fetching
├── backend/Dockerfile       # Backend container config
├── frontend/Dockerfile      # Frontend container config
└── docker-compose.yml       # Multi-service orchestration
```

### Agent Routing Logic

```
User Query
    │
    ├─ Contains "stock", "price", "financial", "market" → Finance Agent
    ├─ Contains "search", "research", "find" → Web Search Agent
    └─ Default → Web Search Agent
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- [Groq API Key](https://console.groq.com/) (free tier available)
- [Finnhub API Key](https://finnhub.io/) (optional, for news)
- Docker & Docker Compose (optional, for containerized deployment)

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/FinaAgent.git
cd FinaAgent
```

### 2. Set Up Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your keys:

```env
GROQ_API_KEY=your_groq_api_key_here
FINNHUB_API_KEY=your_finnhub_api_key_here
FASTAPI_BASE_URL=http://localhost:8000

# Optional — for Langfuse observability
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Application

**Terminal 1 — Start the FastAPI backend:**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 — Start the Streamlit frontend:**
```bash
streamlit run app.py
```

Open your browser at **http://localhost:8501**

---

## 🐳 Docker Deployment

Run the full stack with a single command:

```bash
docker-compose up --build
```

| Service | URL |
|---|---|
| Frontend (Streamlit) | http://localhost:8501 |
| Backend (FastAPI) | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |

---

## 🔌 API Reference

### `POST /query`
Send a natural-language financial question to the multi-agent system.

```json
// Request
{ "prompt": "What is Tesla's current stock price and PE ratio?" }

// Response
{ "response": "TSLA is trading at $XXX.XX with a P/E ratio of..." }
```

### `POST /backtest`
Run a Moving Average crossover backtest on any stock.

```json
// Request
{
  "symbol": "AAPL",
  "fast_window": 10,
  "slow_window": 30,
  "start_date": "2024-01-01",
  "end_date": "2025-01-01"
}
```

### `POST /ai-signal`
Extract an AI trading signal from the latest SEC 10-K filing.

```json
// Request
{ "symbol": "NVDA" }

// Response
{
  "sentiment": "positive",
  "tone_confidence": 0.82,
  "hedge_ratio": 0.18,
  "summary": "..."
}
```

### `GET /health`
Health check endpoint — returns `{"status": "healthy"}`.

---

## 🤖 AI Signal Pipeline

The AI signal pipeline extracts actionable sentiment from SEC 10-K filings:

```
Symbol → SEC EDGAR CIK Lookup
       → Fetch most recent 10-K filing index
       → Extract primary HTML document URL
       → Fetch full document (Item 1A Risk Factors / Item 7 MD&A)
       → Parse with BeautifulSoup → extract 600-2000+ chars of real text
       → Send to Groq LLM (Llama 3.3-70B) for sentiment analysis
       → Return { sentiment, tone_confidence, hedge_ratio }
```

**Supported Tickers for AI Signals:** AAPL, MSFT, GOOGL, AMZN, META, TSLA, NVDA, NFLX, INTC, AMD, QCOM

**Point-in-Time Support:** Pass `as_of_date` to avoid look-ahead bias in walk-forward testing.

---

## 📉 Backtesting Engine

The MA-crossover backtesting engine supports:

- **Technical-only mode**: Pure moving average crossover signals
- **Technical + AI mode**: AI signal filters and scales positions
  - Skips bullish crosses when `sentiment == 'negative'`
  - Reduces position size to `tone_confidence` when hedging language > 30%
- **Ablation testing**: Compare Technical-only vs. Technical+AI equity curves
- **Metrics**: Sharpe Ratio, Sortino Ratio, Max Drawdown, Annualized Return
- **Realistic costs**: Transaction costs (0.1%) + slippage (0.05%) modeled

```
Example Ablation Results (AAPL):
  Technical Only:     Sharpe 0.2943, Max DD -10.78%
  Technical + AI:     Sharpe 0.2943, Max DD  -7.82%   (+27% improvement)
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **LLM Inference** | [Groq](https://groq.com/) — Llama 3.3-70B |
| **Backend** | FastAPI + Uvicorn |
| **Frontend** | Streamlit + Plotly |
| **Market Data** | yFinance |
| **SEC Filings** | SEC EDGAR API + BeautifulSoup |
| **Observability** | Langfuse |
| **Containerization** | Docker + Docker Compose |

---

## 📦 Dependencies

```
openai          # OpenAI-compatible client (used with Groq base URL)
groq            # Groq SDK
fastapi         # REST API framework
uvicorn         # ASGI server
streamlit       # UI framework
pandas          # Data manipulation
numpy           # Numerical computing
python-dotenv   # Environment variable management
yfinance        # Yahoo Finance market data
requests        # HTTP client
plotly          # Interactive charts
pydantic        # Data validation
langfuse        # LLM observability & tracing
beautifulsoup4  # HTML parsing for SEC documents
```

---

## 🧪 Testing

Run the test suite:

```bash
# Test AI signal extraction
python test_document_extraction.py

# Test news fetching
python test_news_fetch.py

# Test backtesting ablation
python test_ablation_fix.py

# Test Langfuse observability
python test_langfuse.py

# Test candlestick chart rendering
python test_candle.py
```

---

## 📁 Project Structure Details

| File | Purpose |
|---|---|
| `main.py` | FastAPI app with `/query`, `/backtest`, `/ai-signal` endpoints |
| `app.py` | Streamlit UI with chat interface, stock dashboard, backtest UI |
| `agent/finance.py` | Finance agent: symbol extraction, data grounding, LLM calls |
| `agent/search.py` | Web search agent for general research queries |
| `agent/system.py` | Routes queries to the correct agent based on intent |
| `ai_signal.py` | SEC 10-K fetching, section extraction, LLM sentiment analysis |
| `backtest_engine.py` | MA-crossover strategy, metrics computation, ablation testing |
| `data_fetcher.py` | Cached yFinance wrapper used by both agents and the dashboard |
| `cache_manager.py` | In-memory TTL caching to reduce API calls |
| `observability.py` | Langfuse trace decorators and structured JSON logging |
| `news_fetcher.py` | Fetches financial news headlines |
| `stock_dashboard.py` | Streamlit components for the stock analysis tab |

---

## 🔐 Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | ✅ Yes | Groq API key for LLM inference |
| `FINNHUB_API_KEY` | ⚠️ Optional | Finnhub key for news data |
| `FASTAPI_BASE_URL` | ✅ Yes | URL of the backend (default: `http://localhost:8000`) |
| `LANGFUSE_SECRET_KEY` | ⚠️ Optional | Langfuse observability secret key |
| `LANGFUSE_PUBLIC_KEY` | ⚠️ Optional | Langfuse observability public key |
| `LANGFUSE_BASE_URL` | ⚠️ Optional | Langfuse host (default: `https://cloud.langfuse.com`) |

---

## 📄 License

This project is for educational and research purposes.

---

## 👤 Author

Built by **Abhishek K** — an AI/ML engineer passionate about quantitative finance and intelligent agent systems.

