import os
import time
from openai import OpenAI
from observability import trace_llm_call_with_langfuse

class BaseAgent:
    def __init__(self, name: str, role: str, instructions: list, tools: list = None):
        self.name = name
        self.role = role
        self.instructions = instructions
        self.tools = tools or []

        # Initialize Groq client
        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY")  # Use Groq API key
        )
        self.model = "llama-3.3-70b-versatile"

    def run(self, question: str):
        # Combine instructions into system prompt
        system_prompt = f"You are {self.name}. {self.role}. Instructions: {' '.join(self.instructions)}"

        start_time = time.time()

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ]
        )

        latency = time.time() - start_time
        result = response.choices[0].message.content

        # Log to Langfuse with full context
        trace_llm_call_with_langfuse(
            system_prompt=system_prompt,
            user_message=question,
            model=self.model,
            response=result,
            latency_ms=latency
        )

        return result