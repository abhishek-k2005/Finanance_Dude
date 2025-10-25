from .finance import FinanceAgent
from .search import WebSearchAgent

class MultiAgentSystem:
    def __init__(self):
        self.agents = {
            "finance": FinanceAgent(),
            "search": WebSearchAgent(),
        }
    
    def query(self, prompt: str) -> str:
        # Parse which agent to use based on prompt
        prompt_lower = prompt.lower()
        
        if "[finance]" in prompt_lower or any(word in prompt_lower for word in ["stock", "financial", "market", "investment", "price"]):
            agent = self.agents["finance"]
            clean_prompt = prompt.replace("[finance]", "").strip()
        elif "[search]" in prompt_lower or any(word in prompt_lower for word in ["search", "research", "find", "look up"]):
            agent = self.agents["search"]
            clean_prompt = prompt.replace("[search]", "").strip()
        else:
            # Default to search agent
            agent = self.agents["search"]
            clean_prompt = prompt
        
        return agent.run(clean_prompt)