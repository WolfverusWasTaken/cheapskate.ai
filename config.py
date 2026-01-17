"""
Configuration management for Carousell Lowballer Agent.
Loads settings from .env file with sensible defaults.
"""

import os
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Literal

# Load environment variables
load_dotenv()


class LLMConfig(BaseModel):
    """LLM provider configuration."""
    provider: Literal["ollama", "gemini"] = "ollama"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "phi3:mini"
    gemini_api_key: str = ""


class AgentConfig(BaseModel):
    """Agent behavior configuration."""
    max_negotiation_rounds: int = 5
    initial_lowball_percent: int = 50
    max_offer_percent: int = 70
    headless_browser: bool = False
    username: str = ""
    password: str = ""


class Config:
    """Main configuration class."""
    
    def __init__(self):
        self.llm = LLMConfig(
            provider=os.getenv("LLM_PROVIDER", "ollama"),
            ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "phi3:mini"),
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        )
        
        self.agent = AgentConfig(
            max_negotiation_rounds=int(os.getenv("MAX_NEGOTIATION_ROUNDS", "5")),
            initial_lowball_percent=int(os.getenv("INITIAL_LOWBALL_PERCENT", "50")),
            max_offer_percent=int(os.getenv("MAX_OFFER_PERCENT", "70")),
            headless_browser=os.getenv("HEADLESS_BROWSER", "false").lower() == "true",
            username=os.getenv("CAROUSELL_USERNAME", ""),
            password=os.getenv("CAROUSELL_PASSWORD", ""),
        )
        
        # Carousell-specific settings
        self.carousell_base_url = "https://www.carousell.sg"
        self.search_url_template = "https://www.carousell.sg/search/{query}"
        
    def get_litellm_model(self) -> str:
        """Get the LiteLLM model string based on provider."""
        if self.llm.provider == "ollama":
            return f"ollama/{self.llm.ollama_model}"
        elif self.llm.provider == "gemini":
            return "gemini/gemini-pro"
        return "ollama/phi3:mini"


# Global config instance
config = Config()
