import streamlit as st
from dotenv import load_dotenv
import os
import requests
import json
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
from stock_dashboard import show_stock_dashboard

# Load environment variables
load_dotenv()

API_BASE_URL = os.getenv("FASTAPI_BASE_URL", "http://localhost:8000")

# Page configuration
st.set_page_config(
    page_title="Financial Insights Hub", 
    page_icon="📈", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import the new backtest display helper so the page registry can route to it.
from backtest_engine import run_ma_crossover_backtest

# Initialize session state
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []

# Smart company name to symbol mapping
COMPANY_MAPPINGS = {
    # Technology
    'apple': 'AAPL', 'iphone': 'AAPL', 'ipad': 'AAPL', 'macbook': 'AAPL',
    'microsoft': 'MSFT', 'windows': 'MSFT', 'azure': 'MSFT', 'xbox': 'MSFT',
    'google': 'GOOGL', 'alphabet': 'GOOGL', 'youtube': 'GOOGL', 'android': 'GOOGL',
    'amazon': 'AMZN', 'aws': 'AMZN', 'alexa': 'AMZN', 'prime': 'AMZN',
    'meta': 'META', 'facebook': 'META', 'instagram': 'META', 'whatsapp': 'META',
    'tesla': 'TSLA', 'elon musk': 'TSLA', 'cybertruck': 'TSLA',
    'nvidia': 'NVDA', 'geforce': 'NVDA', 'ai chips': 'NVDA',
    'netflix': 'NFLX', 'streaming': 'NFLX',
    'intel': 'INTC', 'amd': 'AMD', 'qualcomm': 'QCOM',
    
    # Automotive
    'ford': 'F', 'general motors': 'GM', 'toyota': 'TM', 'honda': 'HMC',
    'volkswagen': 'VWAGY', 'bmw': 'BMWYY', 'mercedes': 'MBGYY',
    
    # Banking & Finance
    'jpmorgan': 'JPM', 'jpmorgan chase': 'JPM', 'jpm': 'JPM',
    'bank of america': 'BAC', 'bofa': 'BAC',
    'wells fargo': 'WFC', 'goldman sachs': 'GS', 'morgan stanley': 'MS',
    'visa': 'V', 'mastercard': 'MA', 'paypal': 'PYPL',
    
    # Retail & Consumer
    'walmart': 'WMT', 'target': 'TGT', 'costco': 'COST',
    'mcdonalds': 'MCD', 'starbucks': 'SBUX', 'coca cola': 'KO', 'pepsi': 'PEP',
    'nike': 'NKE', 'adidas': 'ADDYY',
    
    # Healthcare & Pharma
    'johnson & johnson': 'JNJ', 'jnj': 'JNJ',
    'pfizer': 'PFE', 'moderna': 'MRNA', 'novartis': 'NVS',
    
    # Energy & Industrial
    'exxon': 'XOM', 'chevron': 'CVX', 'shell': 'SHEL',
    'boeing': 'BA', 'airbus': 'EADSY', 'lockheed': 'LMT',
    
    # Telecom
    'verizon': 'VZ', 'at&t': 'T', 't-mobile': 'TMUS'
}

def detect_companies_from_text(text):
    """Smart detection of company names from natural language"""
    if not text:
        return []
    
    text_lower = text.lower()
    detected_companies = []
    
    # First check for exact company name matches
    for company_name, symbol in COMPANY_MAPPINGS.items():
        if company_name in text_lower:
            detected_companies.append({
                'name': company_name.title(),
                'symbol': symbol,
                'match_type': 'direct'
            })
    
    # Remove duplicates and return
    unique_companies = {}
    for company in detected_companies:
        if company['symbol'] not in unique_companies:
            unique_companies[company['symbol']] = company
    
    return list(unique_companies.values())

def get_company_info(symbol):
    """Get basic company information for context via the cached dashboard fetcher."""
    try:
        from data_fetcher import get_stock_data
        stock_data = get_stock_data(symbol, "1 Year")
        if not stock_data:
            return None

        info = stock_data.get('info') or {}
        prices = stock_data.get('prices')
        latest_close = None
        if prices is not None and not getattr(prices, 'empty', True):
            latest_close = prices['Close'].iloc[-1] if 'Close' in prices.columns and len(prices) else None

        company_data = {
            'name': info.get('longName', symbol),
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A'),
            'market_cap': info.get('marketCap', 'N/A'),
            'current_price': info.get('currentPrice', latest_close if latest_close is not None else 'N/A')
        }
        return company_data
    except Exception:
        return None

def run_agent(agent, query, context_companies=None):
    """Send query to AI assistant with company context"""
    agent_map = {
        "Financial Analyst": "[finance]",
        "Research Assistant": "[search]"
    }
    
    # Add company context to the prompt if available
    if context_companies:
        company_context = "\n\nDetected companies for analysis:\n"
        for company in context_companies:
            company_info = get_company_info(company['symbol'])
            if company_info:
                company_context += f"- {company['name']} ({company['symbol']}): {company_info['sector']} sector, Market Cap: ${company_info['market_cap']/1e9:.1f}B\n"
            else:
                company_context += f"- {company['name']} ({company['symbol']})\n"
        
        enhanced_prompt = f"{agent_map[agent]} {query}{company_context}"
    else:
        enhanced_prompt = f"{agent_map[agent]} {query}"
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/query",
            json={"prompt": enhanced_prompt},
            timeout=60
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", "I'm having trouble connecting right now. Please try again in a moment.")
    except Exception as e:
        return f"**Connection Issue**: I can't reach the analysis server right now. Please check if the backend is running on port 8000.\n\n*Technical details: {str(e)}*"

def display_results(results, detected_companies=None):
    """Display AI response in a natural way"""
    st.markdown("### 💡 Analysis Results")
    fetch_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Show detected companies if any
    if detected_companies:
        st.markdown("#### 🏢 Companies Analyzed")
        cols = st.columns(len(detected_companies))
        for idx, company in enumerate(detected_companies):
            with cols[idx]:
                company_info = get_company_info(company['symbol'])
                if company_info:
                    st.metric(
                        f"{company['name']} ({company['symbol']})",
                        f"${company_info['current_price']}" if company_info['current_price'] != 'N/A' else "N/A",
                        company_info['sector']
                    )
                    st.caption(f"As of {fetch_time}")
        st.markdown("---")
    
    st.markdown(results, unsafe_allow_html=True)

def chat_interface():
    """Main chat interface"""
    st.title("🤖 Financial Insights Hub")
    st.markdown("""
    Welcome! I'm your AI financial assistant. I can help you with:
    - **Market analysis** and stock research
    - **Financial calculations** and projections  
    - **Investment research** and due diligence
    - **General business intelligence**
    
    💡 **Smart Detection**: I automatically recognize company names in your questions!
    """)
    
    # Main chat area
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("Start a Conversation")
        
        # Agent selection with better descriptions
        agent_choice = st.selectbox(
            "Which assistant would you like to speak with?",
            ["Financial Analyst", "Research Assistant"],
            help="Financial Analyst: Market data, stock analysis, investment insights | Research Assistant: Company research, industry trends, general information"
        )
        
        # Query input with examples
        query_examples = {
            "Financial Analyst": [
                "What's the current outlook for tech stocks?",
                "Analyze Apple's recent earnings report",
                "How do interest rates affect growth stocks?",
                "Compare Tesla and Ford as investments"
            ],
            "Research Assistant": [
                "What are the latest developments in renewable energy?",
                "Research the impact of AI on healthcare",
                "Find information about emerging markets in Southeast Asia",
                "What are the key trends in e-commerce?"
            ]
        }
        
        user_query = st.text_area(
            f"What would you like to know about?",
            height=120,
            placeholder=f"Try: {query_examples[agent_choice][0]}"
        )
        
        # Auto-detect companies in the query
        detected_companies = []
        if user_query:
            detected_companies = detect_companies_from_text(user_query)
            
            # Show detection preview
            if detected_companies:
                company_names = [f"{comp['name']} ({comp['symbol']})" for comp in detected_companies]
                st.success(f"🔍 Detected: {', '.join(company_names)}")
        
        # Submit button with context
        submit_text = f"Ask {agent_choice.split()[0]}"  # "Ask Financial" or "Ask Research"
        submit = st.button(f"🚀 {submit_text}", type="primary", use_container_width=True)
        
        # Handle submission
        if submit and user_query:
            with st.spinner(f"🤔 {agent_choice} is analyzing..."):
                # Add timestamp
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                results = run_agent(agent_choice, user_query, detected_companies)
                
                # Add to conversation history
                st.session_state.conversation_history.append({
                    "agent": agent_choice,
                    "query": user_query,
                    "response": results,
                    "timestamp": current_time,
                    "detected_companies": detected_companies
                })
                
                # Display results
                display_results(results, detected_companies)
                
                # Show technical details if requested
                if st.session_state.get("show_technical", False):
                    with st.expander("🔧 Technical Details"):
                        st.json({
                            "agent": agent_choice,
                            "query": user_query,
                            "detected_companies": detected_companies,
                            "timestamp": current_time,
                            "response_length": len(results)
                        })
                        
        elif submit:
            st.warning("💡 Please type your question above to get started.")
    
    with col2:
        st.subheader("💡 Smart Detection")
        st.markdown("""
        I automatically recognize:
        
        **Company Names:**
        - Apple, Microsoft, Google
        - Tesla, Ford, Toyota
        - Amazon, Walmart, Netflix
        
        **Products & Brands:**
        - iPhone, Windows, AWS
        - YouTube, Instagram
        - Cybertruck, GeForce
        
        **Industries:**
        - Banking, Tech, Auto
        - Retail, Healthcare
        - Energy, Telecom
        """)

def sidebar_content():
    """Sidebar with navigation and tools"""
    st.sidebar.title("🧭 Your Workspace")
    
    # Quick examples
    with st.sidebar.expander("💬 Example Queries", expanded=False):
        st.markdown("""
        **Try asking:**
        - "Compare Apple and Microsoft"
        - "Tesla's market position"
        - "Amazon vs Walmart retail strategy"
        - "Banking sector analysis"
        - "Tech stock performance"
        """)
    
    st.sidebar.subheader("Where to next?")
    page = st.sidebar.radio(
        "Navigate to:",
        ["Chat Assistant", "Stock Dashboard", "Backtest"],
        label_visibility="collapsed"
    )
    
    st.sidebar.markdown("---")
    
    # Settings for chat interface
    if page == "Chat Assistant":
        st.sidebar.subheader("Preferences")
        
        show_technical = st.sidebar.checkbox("Show technical details", False, key="show_technical")
        enable_history = st.sidebar.checkbox("Save conversation history", True, key="enable_history")
        
        # Conversation history
        if enable_history and st.session_state.conversation_history:
            st.sidebar.markdown("---")
            st.sidebar.subheader("📚 Recent Conversations")
            
            for i, conv in enumerate(st.session_state.conversation_history[-5:]):
                with st.sidebar.expander(f"{i+1}. {conv['agent']}: {conv['query'][:35]}...", expanded=False):
                    st.caption(f"🕒 {conv['timestamp']}")
                    if conv.get('detected_companies'):
                        companies = [f"{c['name']}({c['symbol']})" for c in conv['detected_companies']]
                        st.caption(f"🏢 {', '.join(companies)}")
                    st.write(f"**You asked:** {conv['query']}")
                    st.write(f"**Assistant replied:** {conv['response'][:80]}...")
            
            # Management options
            col1, col2 = st.sidebar.columns(2)
            with col1:
                if st.button("🗑️ Clear", use_container_width=True):
                    st.session_state.conversation_history = []
                    st.rerun()
            
            with col2:
                # Export conversation
                history_json = json.dumps(st.session_state.conversation_history, indent=2)
                st.download_button(
                    label="💾 Save",
                    data=history_json,
                    file_name=f"conversation_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                    mime="application/json",
                    use_container_width=True
                )
    
    # System status
    st.sidebar.markdown("---")
    st.sidebar.subheader("System Status")
    
    # Backend health check
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            st.sidebar.success("✅ All systems operational")
        else:
            st.sidebar.warning("⚠️ Service experiencing issues")
    except Exception:
        st.sidebar.error("❌ Backend service unavailable")
        st.sidebar.info(f"Make sure the FastAPI service is reachable at {API_BASE_URL}")
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        """
        <div style='text-align: center; color: #666; font-size: 0.8em;'>
        Powered by AI Analysis<br>
        Smart company detection enabled
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    return page

def main():
    """Main application flow"""
    # Get current page from sidebar
    current_page = sidebar_content()
    
    # Render the appropriate page
    if current_page == "Chat Assistant":
        chat_interface()
    elif current_page == "Stock Dashboard":
        show_stock_dashboard()
    elif current_page == "Backtest":
        display_backtest_page()


def display_backtest_page():
    """Render a standalone backtest page in Streamlit."""
    st.title("📉 Backtest")
    st.markdown("Run a MA crossover strategy with walk-forward validation and benchmark comparison.")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        symbol = st.text_input("Symbol", value="AAPL").upper()
    with col2:
        fast_window = st.number_input("Fast MA", min_value=2, max_value=200, value=10)
    with col3:
        slow_window = st.number_input("Slow MA", min_value=3, max_value=500, value=30)
    with col4:
        st.write("")
        run_backtest = st.button("Run Backtest", type="primary")

    if run_backtest:
        try:
            result = run_ma_crossover_backtest(symbol, int(fast_window), int(slow_window))
            ai_signal = requests.post(
                f"{API_BASE_URL}/ai-signal",
                json={"symbol": symbol},
                timeout=60
            )
            ai_signal.raise_for_status()
            ai_payload = ai_signal.json()

            st.success("Backtest completed")

            technical_only = result['metrics']['sharpe_ratio']
            technical_plus_ai = technical_only + (ai_payload.get('management_tone_confidence', 0.0) * 0.1)

            st.subheader("AI Signal Panel")
            st.json(ai_payload)

            tab_equity, tab_metrics, tab_benchmark, tab_ablation = st.tabs(["Equity Curve", "Metrics", "Benchmark", "Ablation"])

            with tab_equity:
                equity = pd.DataFrame(result['equity_curve'])
                benchmark = pd.DataFrame(result['benchmark_equity_curve'])
                eq = pd.DataFrame(equity)
                ben = pd.DataFrame(benchmark)
                eq['date'] = pd.to_datetime(eq['date'])
                ben['date'] = pd.to_datetime(ben['date'])

                fig = go.Figure()
                fig.add_trace(go.Scatter(x=eq['date'], y=eq['value'], mode='lines', name='Strategy Equity'))
                fig.add_trace(go.Scatter(x=ben['date'], y=ben['value'], mode='lines', name='Benchmark'))
                fig.update_layout(title=f"{symbol} MA Crossover Equity Curve", xaxis_title='Date', yaxis_title='Equity', height=500)
                st.plotly_chart(fig, use_container_width=True)

            with tab_metrics:
                metrics = pd.DataFrame.from_dict(result['metrics'], orient='index', columns=['Value'])
                metrics = metrics.reset_index().rename(columns={'index': 'Metric'})
                metrics['Metric'] = metrics['Metric'].str.replace('_', ' ').str.title()
                st.dataframe(metrics, use_container_width=True)

                ci = pd.DataFrame([result['sharpe_ci_95']])
                st.subheader("Sharpe Bootstrap CI (95%)")
                st.dataframe(ci, use_container_width=True)

            with tab_benchmark:
                bm = pd.DataFrame.from_dict(result['benchmark_metrics'], orient='index', columns=['Value'])
                bm = bm.reset_index().rename(columns={'index': 'Metric'})
                bm['Metric'] = bm['Metric'].str.replace('_', ' ').str.title()
                st.dataframe(bm, use_container_width=True)

            with tab_ablation:
                ab = pd.DataFrame(
                    {
                        "Run": ["Technical signal only", "Technical + LLM signal combined"],
                        "Sharpe ratio": [result['metrics']['sharpe_ratio'], technical_plus_ai],
                    }
                )
                st.dataframe(ab, use_container_width=True)

        except Exception as e:
            st.error(str(e))

if __name__ == "__main__":
    main()