# import streamlit as st
# from dotenv import load_dotenv
# import os
# import requests
# import json
# from datetime import datetime
# from stock_dashboard import show_stock_dashboard

# # Load environment variables
# load_dotenv()

# # Page configuration
# st.set_page_config(
#     page_title="Financial Insights Hub", 
#     page_icon="📈", 
#     layout="wide",
#     initial_sidebar_state="expanded"
# )

# # Initialize session state
# if 'conversation_history' not in st.session_state:
#     st.session_state.conversation_history = []

# def run_agent(agent, query):
#     """Send query to AI assistant"""
#     agent_map = {
#         "Financial Analyst": "[finance]",
#         "Research Assistant": "[search]"
#     }
    
#     prompt = f"{agent_map[agent]} {query}"
    
#     try:
#         response = requests.post(
#             "http://localhost:8000/query",
#             json={"prompt": prompt},
#             timeout=60
#         )
#         response.raise_for_status()
#         data = response.json()
#         return data.get("response", "I'm having trouble connecting right now. Please try again in a moment.")
#     except Exception as e:
#         return f"**Connection Issue**: I can't reach the analysis server right now. Please check if the backend is running on port 8000.\n\n*Technical details: {str(e)}*"

# def display_results(results):
#     """Display AI response in a natural way"""
#     st.markdown("### 💡 Analysis Results")
#     st.markdown("---")
#     st.markdown(results, unsafe_allow_html=True)

# def chat_interface():
#     """Main chat interface"""
#     st.title("🤖 Financial Insights Hub")
#     st.markdown("""
#     Welcome! I'm your AI financial assistant. I can help you with:
#     - **Market analysis** and stock research
#     - **Financial calculations** and projections  
#     - **Investment research** and due diligence
#     - **General business intelligence**
    
#     Choose an assistant below and let me know what you'd like to explore.
#     """)
    
#     # Main chat area
#     col1, col2 = st.columns([3, 1])
    
#     with col1:
#         st.subheader("Start a Conversation")
        
#         # Agent selection with better descriptions
#         agent_choice = st.selectbox(
#             "Which assistant would you like to speak with?",
#             ["Financial Analyst", "Research Assistant"],
#             help="Financial Analyst: Market data, stock analysis, investment insights | Research Assistant: Company research, industry trends, general information"
#         )
        
#         # Query input with examples
#         query_examples = {
#             "Financial Analyst": [
#                 "What's the current outlook for tech stocks?",
#                 "Analyze Apple's recent earnings report",
#                 "How do interest rates affect growth stocks?",
#                 "Compare Tesla and Ford as investments"
#             ],
#             "Research Assistant": [
#                 "What are the latest developments in renewable energy?",
#                 "Research the impact of AI on healthcare",
#                 "Find information about emerging markets in Southeast Asia",
#                 "What are the key trends in e-commerce?"
#             ]
#         }
        
#         user_query = st.text_area(
#             f"What would you like to know about?",
#             height=120,
#             placeholder=f"Try: {query_examples[agent_choice][0]}"
#         )
        
#         # Submit button with context
#         submit_text = f"Ask {agent_choice.split()[0]}"  # "Ask Financial" or "Ask Research"
#         submit = st.button(f"🚀 {submit_text}", type="primary", use_container_width=True)
        
#         # Handle submission
#         if submit and user_query:
#             with st.spinner(f"🤔 {agent_choice} is thinking..."):
#                 # Add timestamp
#                 current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
#                 results = run_agent(agent_choice, user_query)
                
#                 # Add to conversation history
#                 st.session_state.conversation_history.append({
#                     "agent": agent_choice,
#                     "query": user_query,
#                     "response": results,
#                     "timestamp": current_time
#                 })
                
#                 # Display results
#                 display_results(results)
                
#                 # Show technical details if requested
#                 if st.session_state.get("show_technical", False):
#                     with st.expander("🔧 Technical Details"):
#                         st.json({
#                             "agent": agent_choice,
#                             "query": user_query,
#                             "timestamp": current_time,
#                             "response_length": len(results)
#                         })
                        
#         elif submit:
#             st.warning("💡 Please type your question above to get started.")

# def sidebar_content():
#     """Sidebar with navigation and tools"""
#     st.sidebar.title("🧭 Your Workspace")
    
#     # Navigation
#     st.sidebar.subheader("Where to next?")
#     page = st.sidebar.radio(
#         "Navigate to:",
#         ["Chat Assistant", "Stock Dashboard"],
#         label_visibility="collapsed"
#     )
    
#     st.sidebar.markdown("---")
    
#     # Settings for chat interface
#     if page == "Chat Assistant":
#         st.sidebar.subheader("Preferences")
        
#         show_technical = st.sidebar.checkbox("Show technical details", False, key="show_technical")
#         enable_history = st.sidebar.checkbox("Save conversation history", True, key="enable_history")
        
#         # Conversation history
#         if enable_history and st.session_state.conversation_history:
#             st.sidebar.markdown("---")
#             st.sidebar.subheader("📚 Recent Conversations")
            
#             for i, conv in enumerate(st.session_state.conversation_history[-5:]):
#                 with st.sidebar.expander(f"{i+1}. {conv['agent']}: {conv['query'][:35]}...", expanded=False):
#                     st.caption(f"🕒 {conv['timestamp']}")
#                     st.write(f"**You asked:** {conv['query']}")
#                     st.write(f"**Assistant replied:** {conv['response'][:80]}...")
            
#             # Management options
#             col1, col2 = st.sidebar.columns(2)
#             with col1:
#                 if st.button("🗑️ Clear", use_container_width=True):
#                     st.session_state.conversation_history = []
#                     st.rerun()
            
#             with col2:
#                 # Export conversation
#                 history_json = json.dumps(st.session_state.conversation_history, indent=2)
#                 st.download_button(
#                     label="💾 Save",
#                     data=history_json,
#                     file_name=f"conversation_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
#                     mime="application/json",
#                     use_container_width=True
#                 )
    
#     # System status
#     st.sidebar.markdown("---")
#     st.sidebar.subheader("System Status")
    
#     # Backend health check
#     try:
#         response = requests.get("http://localhost:8000/health", timeout=5)
#         if response.status_code == 200:
#             st.sidebar.success("✅ All systems operational")
#         else:
#             st.sidebar.warning("⚠️ Service experiencing issues")
#     except:
#         st.sidebar.error("❌ Backend service unavailable")
#         st.sidebar.info("Make sure to start the server with: `uvicorn main:app --reload --port 8000`")
    
#     # Footer
#     st.sidebar.markdown("---")
#     st.sidebar.markdown(
#         """
#         <div style='text-align: center; color: #666; font-size: 0.8em;'>
#         Powered by AI Analysis<br>
#         Data updates in real-time
#         </div>
#         """, 
#         unsafe_allow_html=True
#     )
    
#     return page

# def main():
#     """Main application flow"""
#     # Get current page from sidebar
#     current_page = sidebar_content()
    
#     # Render the appropriate page
#     if current_page == "Chat Assistant":
#         chat_interface()
#     elif current_page == "Stock Dashboard":
#         show_stock_dashboard()

# if __name__ == "__main__":
#     main()




import streamlit as st
from dotenv import load_dotenv
import os
import requests
import json
from datetime import datetime
from stock_dashboard import show_stock_dashboard

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Financial Insights Hub", 
    page_icon="📈", 
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    """Get basic company information for context"""
    try:
        import yfinance as yf
        stock = yf.Ticker(symbol)
        info = stock.info
        
        company_data = {
            'name': info.get('longName', symbol),
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A'),
            'market_cap': info.get('marketCap', 'N/A'),
            'current_price': info.get('currentPrice', 'N/A')
        }
        return company_data
    except:
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
            "http://localhost:8000/query",
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
    
    # Navigation
    st.sidebar.subheader("Where to next?")
    page = st.sidebar.radio(
        "Navigate to:",
        ["Chat Assistant", "Stock Dashboard"],
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
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            st.sidebar.success("✅ All systems operational")
        else:
            st.sidebar.warning("⚠️ Service experiencing issues")
    except:
        st.sidebar.error("❌ Backend service unavailable")
        st.sidebar.info("Make sure to start the server with: `uvicorn main:app --reload --port 8000`")
    
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

if __name__ == "__main__":
    main()