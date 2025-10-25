import yfinance as yf
from datetime import datetime
from .base import BaseAgent
import numpy as np
from langchin.groq import Groq

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