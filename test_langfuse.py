#!/usr/bin/env python
"""Quick test: Query AAPL and verify Langfuse trace appears."""
import os
from dotenv import load_dotenv

load_dotenv()

# Debug: verify .env loaded
print(f"LANGFUSE_PUBLIC_KEY: {os.getenv('LANGFUSE_PUBLIC_KEY')[:20]}..." if os.getenv('LANGFUSE_PUBLIC_KEY') else "NOT SET")
print(f"LANGFUSE_SECRET_KEY: {os.getenv('LANGFUSE_SECRET_KEY')[:20]}..." if os.getenv('LANGFUSE_SECRET_KEY') else "NOT SET")

from agent.system import MultiAgentSystem

print("\nInitializing agent system...")
agent_system = MultiAgentSystem()

print("\nRunning AAPL query...\n")
query = "[finance] What is Apple's current stock price and market sentiment?"
response = agent_system.query(query)

print("Response received:")
print(response[:200] + "..." if len(response) > 200 else response)

print("\nQuery complete. Check Langfuse dashboard for trace:")
print("   URL: https://cloud.langfuse.com")
print("   Look for 'llm_call' events in the Traces tab")
