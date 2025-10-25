import requests
from .base import BaseAgent

class WebSearchAgent(BaseAgent):
    def __init__(self):
        instructions = [
            "You are a web research expert.",
            "Provide comprehensive, well-researched information from across the web.",
            "Always summarize key points clearly.",
            "Include relevant sources and citations when possible.",
            "Present information in an organized, easy-to-read format.",
        ]
        
        super().__init__(
            name="Web Search Agent",
            role="Search and provide reliable, relevant information from across the web",
            instructions=instructions,
            tools=[],
        )
    
    def run(self, question: str):
        # Enhanced prompt for web research
        enhanced_prompt = f"""
        Web Research Request: {question}
        
        Provide a comprehensive answer based on general knowledge and web research principles.
        Include:
        1. Key facts and information
        2. Relevant context and background
        3. Current perspectives (if applicable)
        4. Summary of important points
        
        Format your response clearly using markdown.
        """
        
        return super().run(enhanced_prompt)