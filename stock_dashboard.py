import os
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import requests
import numpy as np
from data_fetcher import get_stock_data, calculate_technical_indicators, calculate_rsi

API_BASE_URL = os.getenv("FASTAPI_BASE_URL", "http://localhost:8000")

def show_stock_dashboard():
    st.title("📈 Stock Analysis Dashboard")
    st.markdown("""
    Analyze stock performance with interactive charts and technical indicators.
    Get comprehensive insights for investment decisions.
    """)
    
    # Sidebar for stock selection and parameters
    st.sidebar.header("Stock Analysis Parameters")
    
    # Stock symbol input
    stock_symbol = st.sidebar.text_input(
        "Stock Symbol", 
        value="AAPL",
        help="Enter stock symbol (e.g., AAPL, TSLA, GOOGL)"
    ).upper()
    
    # Analysis period
    analysis_period = st.sidebar.selectbox(
        "Analysis Period",
        options=["1 Year", "2 Years", "5 Years", "Custom"],
        index=0
    )
    
    # Custom date range
    if analysis_period == "Custom":
        col1, col2 = st.sidebar.columns(2)
        with col1:
            start_date = st.date_input("Start Date", datetime.now() - timedelta(days=365))
        with col2:
            end_date = st.date_input("End Date", datetime.now())
    else:
        period_map = {
            "1 Year": "1y",
            "2 Years": "2y", 
            "5 Years": "5y"
        }
        period = period_map[analysis_period]
    
    # Technical indicators
    st.sidebar.header("Technical Indicators")
    show_sma = st.sidebar.checkbox("Moving Averages", value=True)
    show_rsi = st.sidebar.checkbox("RSI", value=True)
    show_volume = st.sidebar.checkbox("Volume", value=True)
    
    if st.sidebar.button("Analyze Stock", type="primary"):
        analyze_stock_data(stock_symbol, analysis_period, show_sma, show_rsi, show_volume)

def analyze_stock_data(symbol, period, show_sma, show_rsi, show_volume):
    """Main function to analyze and display stock data"""
    
    try:
        with st.spinner(f"Fetching data for {symbol}..."):
            # Get stock data
            stock_data = get_stock_data(symbol, period)
            
            if stock_data is None:
                st.error(f"Could not fetch data for {symbol}. Please check the symbol and try again.")
                return
        
        # Display key metrics
        display_key_metrics(stock_data, symbol)
        
        # Price chart
        display_price_chart(stock_data, symbol, show_sma)
        
        # Additional charts
        col1, col2 = st.columns(2)
        
        with col1:
            if show_rsi:
                display_rsi_chart(stock_data, symbol)
            
        with col2:
            if show_volume:
                display_volume_chart(stock_data, symbol)
        
        # Financial analysis from AI agent
        display_ai_analysis(symbol, period)
        
        # Download data
        display_data_export(stock_data, symbol)
        
    except requests.exceptions.Timeout as e:
        st.error(f"API timeout while analyzing {symbol}: {type(e).__name__}: {e}")
    except requests.exceptions.HTTPError as e:
        st.error(f"Rate limit or API response error while analyzing {symbol}: {type(e).__name__}: {e}")
    except (ValueError, KeyError) as e:
        st.error(f"Invalid symbol or no data for range while analyzing {symbol}: {type(e).__name__}: {e}")
    except Exception as e:
        error_type = type(e).__name__
        message = str(e)
        if "Invalid symbol" in message or "symbol" in message.lower() and "not found" in message.lower():
            st.error(f"Invalid symbol {symbol}: {error_type}: {message}")
        elif "429" in message or "Too Many Requests" in message or "rate limit" in message.lower():
            st.error(f"Rate limit exceeded for {symbol}: {error_type}: {message}")
        elif "No data" in message or "no data" in message.lower() or "empty" in message.lower():
            st.error(f"No data for range for {symbol}: {error_type}: {message}")
        else:
            st.error(f"Analysis failed for {symbol}: {error_type}: {message}")


def display_key_metrics(stock_data, symbol):
    """Display key financial metrics"""
    st.header(f"📊 Key Metrics for {symbol}")
    fetch_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"As of {fetch_time}")
    
    prices = stock_data['prices']
    info = stock_data['info']
    
    # Calculate metrics
    current_price = prices['Close'].iloc[-1]
    prev_close = prices['Close'].iloc[-2] if len(prices) > 1 else current_price
    price_change = current_price - prev_close
    price_change_pct = (price_change / prev_close) * 100
    
    # Create metrics columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Current Price", 
            f"${current_price:.2f}",
            f"{price_change:+.2f} ({price_change_pct:+.2f}%)"
        )
    
    with col2:
        market_cap = info.get('marketCap', 'N/A')
        if market_cap != 'N/A':
            market_cap_str = f"${market_cap/1e9:.2f}B" if market_cap > 1e9 else f"${market_cap/1e6:.2f}M"
        else:
            market_cap_str = 'N/A'
        st.metric("Market Cap", market_cap_str)
    
    with col3:
        pe_ratio = info.get('trailingPE', 'N/A')
        st.metric("P/E Ratio", f"{pe_ratio:.2f}" if pe_ratio != 'N/A' else 'N/A')
    
    with col4:
        volume = prices['Volume'].iloc[-1]
        volume_str = f"{volume/1e6:.1f}M" if volume > 1e6 else f"{volume/1e3:.0f}K"
        st.metric("Volume", volume_str)
    
    # Additional metrics
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        day_high = prices['High'].iloc[-1]
        day_low = prices['Low'].iloc[-1]
        st.metric("Day Range", f"${day_low:.2f} - ${day_high:.2f}")
    
    with col6:
        fifty_two_high = info.get('fiftyTwoWeekHigh', 'N/A')
        fifty_two_low = info.get('fiftyTwoWeekLow', 'N/A')
        st.metric("52W Range", f"${fifty_two_low:.2f} - ${fifty_two_high:.2f}")
    
    with col7:
        dividend_yield = info.get('dividendYield', 'N/A')
        st.metric("Dividend Yield", 
                 f"{dividend_yield:.2f}%" if dividend_yield != 'N/A' else 'N/A')
    
    with col8:
        beta = info.get('beta', 'N/A')
        st.metric("Beta", f"{beta:.2f}" if beta != 'N/A' else 'N/A')

def display_price_chart(stock_data, symbol, show_sma):
    """Display interactive price chart"""
    st.header("📈 Price Chart")
    
    prices = stock_data['prices']
    
    fig = go.Figure()
    
    # Candlestick chart
    fig.add_trace(go.Candlestick(
        x=prices.index,
        open=prices['Open'],
        high=prices['High'],
        low=prices['Low'],
        close=prices['Close'],
        name='Price'
    ))
    
    # Moving averages
    if show_sma:
        fig.add_trace(go.Scatter(
            x=prices.index, y=prices['SMA_20'],
            line=dict(color='orange', width=1),
            name='SMA 20'
        ))
        fig.add_trace(go.Scatter(
            x=prices.index, y=prices['SMA_50'],
            line=dict(color='green', width=1),
            name='SMA 50'
        ))
        fig.add_trace(go.Scatter(
            x=prices.index, y=prices['SMA_200'],
            line=dict(color='red', width=1),
            name='SMA 200'
        ))
    
    fig.update_layout(
        title=f"{symbol} Stock Price",
        xaxis_title="Date",
        yaxis_title="Price ($)",
        height=500,
        showlegend=True
    )
    
    st.plotly_chart(fig, use_container_width=True)

def display_rsi_chart(stock_data, symbol):
    """Display RSI chart"""
    prices = stock_data['prices']
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=prices.index, y=prices['RSI'],
        line=dict(color='purple', width=2),
        name='RSI'
    ))
    
    # Add overbought/oversold lines
    fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought")
    fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold")
    
    fig.update_layout(
        title=f"{symbol} RSI (14)",
        xaxis_title="Date",
        yaxis_title="RSI",
        height=300
    )
    
    st.plotly_chart(fig, use_container_width=True)

def display_volume_chart(stock_data, symbol):
    """Display volume chart"""
    prices = stock_data['prices']
    
    fig = go.Figure()
    
    # Color volume bars based on price movement
    colors = ['red' if prices['Close'][i] < prices['Open'][i] else 'green' 
              for i in range(len(prices))]
    
    fig.add_trace(go.Bar(
        x=prices.index,
        y=prices['Volume'],
        marker_color=colors,
        name='Volume'
    ))
    
    fig.update_layout(
        title=f"{symbol} Trading Volume",
        xaxis_title="Date",
        yaxis_title="Volume",
        height=300
    )
    
    st.plotly_chart(fig, use_container_width=True)

def display_ai_analysis(symbol, period):
    """Get AI analysis for the stock"""
    st.header("🤖 AI Financial Analysis")
    
    prompt = f"""
    Provide a comprehensive financial analysis for {symbol} over the {period} period.
    
    Include:
    1. Technical analysis summary
    2. Key support and resistance levels
    3. Trend analysis
    4. Risk assessment
    5. Investment recommendation
    6. Price targets if possible
    
    Be professional and data-driven in your analysis.
    """
    
    try:
        with st.spinner("Generating AI analysis..."):
            response = requests.post(
                f"{API_BASE_URL}/query",
                json={"prompt": f"[finance] {prompt}"},
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                st.markdown(data.get("response", "No analysis available."))
            else:
                st.error("Failed to get AI analysis. Please try again.")
                
    except Exception as e:
        st.error(f"Error getting AI analysis: {str(e)}")

def display_data_export(stock_data, symbol):
    """Allow users to download the data"""
    st.header("📥 Export Data")
    
    prices = stock_data['prices']
    
    # Convert to downloadable format
    csv = prices.to_csv()
    json_str = prices.to_json(orient='split', date_format='iso')
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"{symbol}_stock_data.csv",
            mime="text/csv"
        )
    
    with col2:
        st.download_button(
            label="Download JSON",
            data=json_str,
            file_name=f"{symbol}_stock_data.json",
            mime="application/json"
        )

# For standalone testing
if __name__ == "__main__":
    show_stock_dashboard()