FinaAgent/
│
├── main.py               ← FastAPI server (entry point for backend)
├── app.py                ← Streamlit frontend (entry point for UI)
├── data_fetcher.py       ← Stock data layer (Finnhub + yfinance + cache)
├── stock_dashboard.py    ← Stock dashboard page (charts, metrics, news)
├── backtest_engine.py    ← MA crossover backtest + walk-forward validation
├── ai_signal.py          ← SEC 10-K NLP + LLM signal + news sentiment
├── news_fetcher.py       ← Finnhub /company-news API wrapper
├── observability.py      ← Langfuse tracing + groundedness checks
├── cache_manager.py      ← (Extra cache utilities)
│
├── agent/
│   ├── base.py           ← BaseAgent: wraps Groq LLM + Langfuse logging
│   ├── finance.py        ← FinanceAgent: stock grounding + LLM analysis
│   ├── search.py         ← WebSearchAgent: general research via LLM
│   └── system.py         ← MultiAgentSystem: routes queries to right agent
│
├── backend/
│   ├── Dockerfile        ← Docker image for FastAPI backend
│   └── requirements.txt  ← Backend Python dependencies
│
├── frontend/
│   └── Dockerfile        ← Docker image for Streamlit frontend
│
├── docker-compose.yml    ← Orchestrates both containers on a shared network
└── .env.example          ← Template for API keys
