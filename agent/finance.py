import json
import re
import time
from datetime import datetime

import yfinance as yf
from data_fetcher import get_stock_data as dashboard_get_stock_data
from .base import BaseAgent
import numpy as np

COMPANY_NAME_TO_SYMBOL = {
    "apple": "AAPL",
    "microsoft": "MSFT",
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "amazon": "AMZN",
    "meta": "META",
    "facebook": "META",
    "tesla": "TSLA",
    "nvidia": "NVDA",
    "netflix": "NFLX",
    "intel": "INTC",
    "amd": "AMD",
    "qualcomm": "QCOM",
}

class FinanceAgent(BaseAgent):
    def __init__(self):
        instructions = [
            "You are a financial analyst expert with access to real-time stock data.",
            "Provide detailed financial analysis including stock prices, fundamentals, and market trends.",
            "Format data in clear markdown tables when possible.",
            "Include dates, percentages, and relevant financial metrics.",
            "Be accurate with financial terminology and calculations.",
        ]
        
        super().__init__(
            name="Finance AI Agent",
            role="Analyze and report on financial data and market trends",
            instructions=instructions,
            tools=[],
        )

    def extract_symbols_from_question(self, question: str):
        """Detect symbols or company names from a finance question."""
        text = question or ""
        text_lower = text.lower()
        symbols = []

        # Company-name grounded extraction
        for company, symbol in COMPANY_NAME_TO_SYMBOL.items():
            if company in text_lower:
                symbols.append(symbol)

        # Direct ticker extraction if a user wrote AAPL/MSFT in the text
        found_tickers = re.findall(r'\b[A-Z]{1,5}\b', text)
        for symbol in found_tickers:
            symbol = symbol.upper()
            if len(symbol) <= 5 and symbol not in symbols:
                symbols.append(symbol)

        return symbols

    def build_grounding_prompt(self, question: str, symbols):
        """Fetch stock data directly from yfinance and pass only those numbers to the LLM."""
        fetch_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        grounded_payload = []

        for symbol in symbols:
            try:
                stock = yf.Ticker(symbol)
                info = stock.info or {}
                prices = stock.history(period="1y")

                if prices is None or prices.empty:
                    grounded_payload.append({
                        "symbol": symbol.upper(),
                        "error": "No stock data returned by yfinance fetch",
                        "fetch_time": fetch_time,
                    })
                    continue

                try:
                    latest_close = prices['Close'].iloc[-1]
                except Exception:
                    latest_close = None

                grounding_row = {
                    "symbol": symbol.upper(),
                    "fetch_time": fetch_time,
                    "current_price": info.get('currentPrice', 'N/A'),
                    "market_cap": info.get('marketCap', 'N/A'),
                    "trailing_pe": info.get('trailingPE', 'N/A'),
                    "dividend_yield": info.get('dividendYield', 'N/A'),
                    "fifty_two_week_high": info.get('fiftyTwoWeekHigh', 'N/A'),
                    "fifty_two_week_low": info.get('fiftyTwoWeekLow', 'N/A'),
                    "beta": info.get('beta', 'N/A'),
                    "latest_close": latest_close,
                    "price_history_tail": prices.tail(5).to_dict('records') if prices is not None and not prices.empty else [],
                }
                grounded_payload.append(grounding_row)

            except Exception as e:
                grounded_payload.append({
                    "symbol": symbol.upper(),
                    "error": f"{type(e).__name__}: {e}",
                    "fetch_time": fetch_time,
                })
                continue

        data_text = json.dumps(grounded_payload, default=str)

        return f"""
Financial Analysis Request: {question}

Grounding data fetched from the yfinance stock-data API:
{data_text}

Instructions for the answer:
Use ONLY the numbers provided below. Do not state any financial figures from your own knowledge.
Compare the requested symbols using the values above only.
"""

    def build_multi_symbol_comparison_prompt(self, question: str, symbols):
        """Fetch each requested symbol through the dashboard helper and create one grounded comparison payload."""
        fetch_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        grounded_payload = []

        for idx, symbol in enumerate(symbols):
            symbol = symbol.upper()
            if idx > 0:
                time.sleep(1.5)
            try:
                stock_data = dashboard_get_stock_data(symbol, "1 Year")

                if stock_data is None:
                    grounded_payload.append({
                        "symbol": symbol,
                        "error": "No dashboard data returned by yfinance fetch",
                        "fetch_time": fetch_time,
                    })
                    continue

                prices = stock_data.get('prices')
                info = stock_data.get('info') or {}

                if prices is None or getattr(prices, 'empty', True):
                    grounded_payload.append({
                        "symbol": symbol,
                        "error": "No stock history returned by dashboard fetch",
                        "fetch_time": fetch_time,
                    })
                    continue

                latest_close = prices['Close'].iloc[-1] if 'Close' in prices.columns and len(prices) else None
                grounding_row = {
                    "symbol": symbol,
                    "fetch_time": fetch_time,
                    "current_price": info.get('currentPrice', latest_close),
                    "market_cap": info.get('marketCap', 'N/A'),
                    "trailing_pe": info.get('trailingPE', 'N/A'),
                    "dividend_yield": info.get('dividendYield', 'N/A'),
                    "fifty_two_week_high": info.get('fiftyTwoWeekHigh', 'N/A'),
                    "fifty_two_week_low": info.get('fiftyTwoWeekLow', 'N/A'),
                    "beta": info.get('beta', 'N/A'),
                    "latest_close": latest_close,
                    "price_history_tail": prices.tail(5).to_dict('records') if prices is not None and not prices.empty else [],
                }
                grounded_payload.append(grounding_row)

            except Exception as e:
                grounded_payload.append({
                    "symbol": symbol,
                    "error": f"{type(e).__name__}: {e}",
                    "fetch_time": fetch_time,
                })

        data_text = json.dumps(grounded_payload, default=str)

        return f"""
Financial Analysis Request: {question}

Grounding data fetched separately from the yfinance dashboard API for each requested symbol:
{data_text}

Instructions for the answer:
Use ONLY the numbers provided below. Do not state any financial figures from your own knowledge.
Compare the requested symbols using the values above only.
Return the answer as a JSON object with a top-level "comparison" array of symbol rows and a top-level "summary" string. Do not return a prose essay.
The JSON must only include values that are present in the grounding payload above.
"""
    
    def get_stock_data(self, symbol: str):
        """Get real stock data using yfinance"""
        try:
            stock = yf.Ticker(symbol)
            info = stock.info
            hist = stock.history(period="1mo")
            
            current_price = info.get('currentPrice', 'N/A')
            pe_ratio = info.get('trailingPE', 'N/A')
            market_cap = info.get('marketCap', 'N/A')
            dividend_yield = info.get('dividendYield', 'N/A')
            
            return {
                'symbol': symbol.upper(),
                'current_price': current_price,
                'pe_ratio': pe_ratio,
                'market_cap': market_cap,
                'dividend_yield': dividend_yield,
                'price_history': hist.tail(5).to_dict() if not hist.empty else {}
            }
        except Exception as e:
            return f"Error fetching data: {str(e)}"
    
    def run(self, question: str):
        symbols = self.extract_symbols_from_question(question)

        if len(symbols) > 1:
            grounded_prompt = self.build_multi_symbol_comparison_prompt(question, symbols)
            return super().run(grounded_prompt)

        if symbols:
            grounded_prompt = self.build_grounding_prompt(question, symbols)
            return super().run(grounded_prompt)

        # Enhanced prompt with financial context
        enhanced_prompt = f"""
        Financial Analysis Request: {question}
        
        As a financial analyst, provide:
        1. Comprehensive analysis
        2. Key financial metrics if discussing specific stocks
        3. Market trends and insights
        4. Risk factors and opportunities
        5. Professional recommendations
        
        Format your response using markdown with clear sections.
        """
        
        return super().run(enhanced_prompt)
    


    
# Add this method to your existing FinanceAgent class
def analyze_stock_performance(self, symbol: str, period: str) -> str:
    """Enhanced analysis for dashboard"""
    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period=period)
        
        if data.empty:
            return f"No data available for {symbol} over {period} period."
        
        # Calculate performance metrics
        start_price = data['Close'].iloc[0]
        end_price = data['Close'].iloc[-1]
        total_return = ((end_price - start_price) / start_price) * 100
        volatility = data['Close'].pct_change().std() * np.sqrt(252) * 100
        
        analysis_prompt = f"""
        Perform comprehensive analysis for {symbol} over {period}:
        
        Performance Metrics:
        - Starting Price: ${start_price:.2f}
        - Current Price: ${end_price:.2f}
        - Total Return: {total_return:+.2f}%
        - Annualized Volatility: {volatility:.2f}%
        
        Provide:
        1. Technical analysis with key levels
        2. Trend identification
        3. Risk assessment
        4. Trading recommendations
        5. Support and resistance levels
        6. Comparison to market benchmarks if relevant
        """
        
        return self.run(analysis_prompt)
        
    except Exception as e:
        return f"Error analyzing {symbol}: {str(e)}"