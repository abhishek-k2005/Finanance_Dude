import os
from openai import OpenAI

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
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ]
        )
        return response.choices[0].message.content