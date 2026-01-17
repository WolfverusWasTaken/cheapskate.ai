"""
LLM Factory - Unified LLM Interface
Purpose: Provides LiteLLM-based abstraction for switching between Ollama and Gemini

Provides:
- LLMFactory.from_env() → creates LLM client based on .env settings
- Unified completion interface for all agent modules
"""

import os
import json
from typing import Optional, Callable, Any
from config import config

try:
    import litellm
    from litellm import completion
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False
    print("LLM_FACTORY: Warning - LiteLLM not installed, using mock mode")


class LLMClient:
    """
    Unified LLM client that wraps LiteLLM for provider-agnostic completions.
    Supports Ollama (local) and Gemini (cloud) backends.
    """
    
    def __init__(
        self,
        model: str,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.7,
    ):
        """
        Initialize the LLM client.
        
        Args:
            model: LiteLLM model string (e.g., "ollama/phi3:mini", "gemini/gemini-pro")
            api_base: API base URL for self-hosted models
            api_key: API key for cloud providers
            temperature: Generation temperature
        """
        self.model = model
        self.api_base = api_base
        self.api_key = api_key
        self.temperature = temperature
        
        # Configure LiteLLM
        if LITELLM_AVAILABLE:
            litellm.set_verbose = False
            if api_base:
                os.environ["OLLAMA_API_BASE"] = api_base
            if api_key:
                os.environ["GEMINI_API_KEY"] = api_key
        
        print(f"LLM_FACTORY: Initialized with model={model}")
    
    async def complete(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        max_tokens: int = 1024,
    ) -> dict:
        """
        Generate a completion from the LLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: Optional list of tool definitions for function calling
            max_tokens: Maximum tokens to generate
            
        Returns:
            Dictionary with 'content', 'tool_calls', and 'raw_response'
        """
        if not LITELLM_AVAILABLE:
            return self._mock_complete(messages, tools)
        
        try:
            print(f"LLM_FACTORY: Generating completion ({len(messages)} messages)...")
            
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": max_tokens,
            }
            
            if self.api_base and "ollama" in self.model:
                kwargs["api_base"] = self.api_base
            
            # Add tools if provided
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"
            
            response = completion(**kwargs)
            
            # Parse response
            message = response.choices[0].message
            result = {
                "content": message.content or "",
                "tool_calls": [],
                "raw_response": response,
            }
            
            # Parse tool calls if present
            if hasattr(message, 'tool_calls') and message.tool_calls:
                for tc in message.tool_calls:
                    result["tool_calls"].append({
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": json.loads(tc.function.arguments),
                    })
            
            print(f"LLM_FACTORY: ✓ Generated {len(result['content'])} chars")
            if result["tool_calls"]:
                print(f"LLM_FACTORY: ✓ Tool calls: {[tc['name'] for tc in result['tool_calls']]}")
            
            return result
            
        except Exception as e:
            print(f"LLM_FACTORY: ✗ Completion failed → {e}")
            return {"content": f"Error: {e}", "tool_calls": [], "error": str(e)}
    
    def complete_sync(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        max_tokens: int = 1024,
    ) -> dict:
        """Synchronous version of complete for non-async contexts."""
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            self.complete(messages, tools, max_tokens)
        )
    
    def _mock_complete(self, messages: list[dict], tools: Optional[list] = None) -> dict:
        """Mock completion for testing without LLM."""
        print("LLM_FACTORY: Using mock completion (LiteLLM not available)")
        
        last_message = messages[-1]["content"] if messages else ""
        
        # Simple mock responses based on keywords
        if "search" in last_message.lower():
            return {
                "content": "I'll search for those items on Carousell.",
                "tool_calls": [{"id": "mock-1", "name": "search_carousell", "arguments": {"query": "iphone"}}],
            }
        elif "negotiate" in last_message.lower() or "lowball" in last_message.lower():
            return {
                "content": "Hi! That looks great. Would you consider $350 cash for quick pickup today?",
                "tool_calls": [],
            }
        else:
            return {
                "content": "I understand. How can I help you with Carousell?",
                "tool_calls": [],
            }
    
    def generate_lowball_message(self, listing_price: float, item_name: str, round_num: int = 1) -> str:
        """
        Generate a lowball negotiation message.
        
        Args:
            listing_price: Original listing price
            item_name: Name of the item
            round_num: Negotiation round number
            
        Returns:
            Generated lowball message
        """
        initial_percent = config.agent.initial_lowball_percent
        max_percent = config.agent.max_offer_percent
        
        # Calculate offer based on round
        if round_num == 1:
            offer_percent = initial_percent
        else:
            # Increase offer each round, up to max
            offer_percent = min(initial_percent + (round_num - 1) * 10, max_percent)
        
        offer_price = int(listing_price * (offer_percent / 100))
        
        messages = [
            {
                "role": "system",
                "content": """You are a friendly but savvy buyer negotiating on Carousell Singapore.
Your goal is to get a good deal while being polite. Write natural, casual messages.
Keep messages short (1-2 sentences). Be friendly but firm on price."""
            },
            {
                "role": "user",
                "content": f"""Generate a lowball message for this item:
Item: {item_name}
Listed Price: S${listing_price}
My Offer: S${offer_price} ({offer_percent}% of listed price)
Round: {round_num}

Write a natural negotiation message."""
            }
        ]
        
        if not LITELLM_AVAILABLE:
            # Fallback messages for mock mode
            fallbacks = [
                f"Hi! Interested in your {item_name}. Can do ${offer_price} cash, pickup today?",
                f"Hey! Would you take ${offer_price} for quick deal? Can collect anytime.",
                f"Hello! Best I can do is ${offer_price}. Looking to buy today if price works!",
            ]
            import random
            return random.choice(fallbacks)
        
        try:
            response = completion(
                model=self.model,
                messages=messages,
                temperature=0.8,
                max_tokens=100,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"LLM_FACTORY: ✗ Message generation failed → {e}")
            return f"Hi! Would you take ${offer_price} for quick pickup today?"


class LLMFactory:
    """Factory for creating LLM clients based on configuration."""
    
    @staticmethod
    def from_env() -> LLMClient:
        """
        Create an LLM client based on environment configuration.
        
        Returns:
            Configured LLMClient instance
        """
        provider = config.llm.provider
        
        if provider == "ollama":
            return LLMClient(
                model=f"ollama/{config.llm.ollama_model}",
                api_base=config.llm.ollama_url,
            )
        elif provider == "gemini":
            return LLMClient(
                model="gemini/gemini-pro",
                api_key=config.llm.gemini_api_key,
            )
        else:
            print(f"LLM_FACTORY: Unknown provider '{provider}', defaulting to Ollama")
            return LLMClient(
                model="ollama/phi3:mini",
                api_base="http://localhost:11434",
            )
    
    @staticmethod
    def create_ollama(model: str = "phi3:mini", url: str = "http://localhost:11434") -> LLMClient:
        """Create an Ollama client with explicit settings."""
        return LLMClient(model=f"ollama/{model}", api_base=url)
    
    @staticmethod
    def create_gemini(api_key: str) -> LLMClient:
        """Create a Gemini client with explicit API key."""
        return LLMClient(model="gemini/gemini-pro", api_key=api_key)


# Standalone test
if __name__ == "__main__":
    import asyncio
    
    print("=" * 50)
    print("LLM FACTORY TEST")
    print("=" * 50)
    
    # Test factory creation
    llm = LLMFactory.from_env()
    print(f"✓ Created LLM client: {llm.model}")
    
    # Test lowball message generation
    message = llm.generate_lowball_message(800, "iPhone 14 Pro", round_num=1)
    print(f"\n✓ Generated lowball message:")
    print(f"  '{message}'")
    
    # Test completion (async)
    async def test_completion():
        result = await llm.complete([
            {"role": "user", "content": "Search for iPhone deals under $600"}
        ])
        print(f"\n✓ Completion result:")
        print(f"  Content: {result['content'][:100]}...")
        if result.get("tool_calls"):
            print(f"  Tool calls: {result['tool_calls']}")
    
    asyncio.run(test_completion())
    
    print("\nLLM_FACTORY: ✓ All tests passed!")
