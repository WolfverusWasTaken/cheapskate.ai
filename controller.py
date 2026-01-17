"""
MODULE 4: Controller Agent (Dev 3)
Purpose: Main orchestrating agent with tool-calling for Carousell automation

Provides:
- ControllerAgent with tools: search_carousell, extract_listings, open_chat, delegate_lowball
- Tool-calling loop: prompt → tools → observations → repeat
- Manages browser navigation and delegates to specialist agents
"""

import asyncio
import json
import re
from typing import Optional, Callable, Any
from datetime import datetime

from browser_loader import BrowserLoader
from dom_extractor import extract_dom
from dom_parser import parse_listings, filter_listings_by_price, format_listings_for_display, extract_listing_details
from llm_factory import LLMClient, LLMFactory
from config import config


class ControllerAgent:
    """
    Main orchestrating agent that controls browser automation and delegates tasks.
    Uses LLM tool-calling to interpret user commands and execute appropriate actions.
    """
    
    def __init__(self, llm: LLMClient, browser_loader: BrowserLoader):
        """
        Initialize the controller agent.
        
        Args:
            llm: LLM client for generating responses and tool calls
            browser_loader: Browser loader instance for page access
        """
        self.llm = llm
        self.browser = browser_loader
        self.current_listings: list[dict] = []
        self.conversation_history: list[dict] = []
        self.lowballer = None  # Lazy-loaded
        
        # Define available tools
        self.tools = self._define_tools()
        self.tool_handlers = self._define_tool_handlers()
        
        print("CONTROLLER: Agent initialized with tools:", list(self.tool_handlers.keys()))
    
    def _define_tools(self) -> list[dict]:
        """Define the tool schemas for LLM function calling."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_carousell",
                    "description": "Search for items on Carousell Singapore. Use this when the user wants to find listings.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query (e.g., 'iPhone 14', 'MacBook Pro')"
                            },
                            "max_price": {
                                "type": "number",
                                "description": "Optional maximum price filter"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "extract_listings",
                    "description": "Extract and display current listings from the search results page.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "open_listing",
                    "description": "Open a specific listing by its index number from the extracted listings.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "listing_index": {
                                "type": "integer",
                                "description": "The index number of the listing to open (from extract_listings results)"
                            }
                        },
                        "required": ["listing_index"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "open_chat",
                    "description": "Open the chat window for a specific seller/listing.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "listing_index": {
                                "type": "integer",
                                "description": "The index number of the listing to chat about"
                            }
                        },
                        "required": ["listing_index"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delegate_lowball",
                    "description": "Delegate negotiation to the Lowballer agent for a specific listing.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "listing_index": {
                                "type": "integer",
                                "description": "The index of the listing to negotiate"
                            }
                        },
                        "required": ["listing_index"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "take_screenshot",
                    "description": "Take a screenshot of the current browser page.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filename": {
                                "type": "string",
                                "description": "Optional filename for the screenshot"
                            }
                        },
                        "required": []
                    }
                }
            },
        ]
    
    def _define_tool_handlers(self) -> dict[str, Callable]:
        """Map tool names to handler functions."""
        return {
            "search_carousell": self._handle_search,
            "extract_listings": self._handle_extract,
            "open_listing": self._handle_open_listing,
            "open_chat": self._handle_open_chat,
            "delegate_lowball": self._handle_delegate_lowball,
            "take_screenshot": self._handle_screenshot,
        }
    
    async def run(self, user_prompt: str) -> str:
        """
        Process a user prompt through the agent loop.
        
        Args:
            user_prompt: The user's command or question
            
        Returns:
            Agent's response string
        """
        print(f"\nCONTROLLER: Processing → '{user_prompt}'")
        
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_prompt
        })
        
        # Build messages for LLM
        messages = self._build_messages()
        
        # Get LLM response with potential tool calls
        response = await self.llm.complete(messages, tools=self.tools)
        
        # Handle tool calls if present
        if response.get("tool_calls"):
            return await self._execute_tool_calls(response["tool_calls"])
        
        # Otherwise, return the content response
        content = response.get("content", "I'm not sure how to help with that.")
        self.conversation_history.append({
            "role": "assistant",
            "content": content
        })
        
        return content
    
    def _build_messages(self) -> list[dict]:
        """Build the message list for the LLM."""
        system_message = {
            "role": "system",
            "content": """You are Carousell Lowballer, an AI assistant that helps users find and negotiate deals on Carousell Singapore.

You have access to these tools:
- search_carousell(query, max_price): Search for items
- extract_listings(): Get current listings from page
- open_listing(listing_index): View a specific listing
- open_chat(listing_index): Open chat with seller
- delegate_lowball(listing_index): Start negotiation
- take_screenshot(): Capture current page

When the user asks to find items, use search_carousell first, then extract_listings to show results.
When they want to negotiate, use delegate_lowball to start the lowball negotiation.

Be helpful, proactive, and explain what you're doing."""
        }
        
        return [system_message] + self.conversation_history[-10:]  # Keep last 10 messages
    
    async def _execute_tool_calls(self, tool_calls: list[dict]) -> str:
        """Execute tool calls and return combined results."""
        results = []
        
        for tc in tool_calls:
            tool_name = tc.get("name")
            arguments = tc.get("arguments", {})
            
            print(f"CONTROLLER: Executing tool '{tool_name}' with args: {arguments}")
            
            handler = self.tool_handlers.get(tool_name)
            if handler:
                try:
                    result = await handler(**arguments)
                    results.append(f"✓ {tool_name}: {result}")
                except Exception as e:
                    results.append(f"✗ {tool_name}: Error - {e}")
            else:
                results.append(f"✗ Unknown tool: {tool_name}")
        
        combined_result = "\n".join(results)
        
        # Add to conversation history
        self.conversation_history.append({
            "role": "assistant",
            "content": combined_result
        })
        
        return combined_result
    
    # Tool Handlers
    
    async def _handle_search(self, query: str, max_price: Optional[float] = None) -> str:
        """Handle search_carousell tool."""
        page = self.browser.get_page()
        if not page:
            return "Browser not ready. Please ensure browser is launched."
        
        # Format search URL
        formatted_query = query.replace(" ", "%20")
        search_url = f"https://www.carousell.sg/search/{formatted_query}"
        
        print(f"CONTROLLER: Searching Carousell for '{query}'...")
        
        success = await self.browser.navigate(search_url)
        if not success:
            return f"Failed to navigate to search results for '{query}'"
        
        # Wait for results to load
        await asyncio.sleep(2)
        
        # Extract listings
        dom_data = await extract_dom(page)
        self.current_listings = parse_listings(dom_data)
        
        # Apply price filter if specified
        if max_price:
            self.current_listings = filter_listings_by_price(self.current_listings, max_price)
        
        return f"Found {len(self.current_listings)} listings for '{query}'" + (f" under ${max_price}" if max_price else "")
    
    async def _handle_extract(self) -> str:
        """Handle extract_listings tool."""
        if not self.current_listings:
            page = self.browser.get_page()
            if page:
                dom_data = await extract_dom(page)
                self.current_listings = parse_listings(dom_data)
        
        if not self.current_listings:
            return "No listings found. Try searching first."
        
        display = format_listings_for_display(self.current_listings)
        print(display)
        return f"Extracted {len(self.current_listings)} listings (displayed above)"
    
    async def _handle_open_listing(self, listing_index: int) -> str:
        """Handle open_listing tool."""
        if not self.current_listings:
            return "No listings available. Search first."
        
        if listing_index < 0 or listing_index >= len(self.current_listings):
            return f"Invalid listing index. Valid range: 0-{len(self.current_listings)-1}"
        
        listing = self.current_listings[listing_index]
        url = listing.get("listing_url")
        
        if not url:
            return f"No URL available for listing {listing_index}"
        
        success = await self.browser.navigate(url)
        if success:
            await asyncio.sleep(1)  # Wait for page load
            return f"Opened listing: {listing['title']} (${listing['price']})"
        return f"Failed to open listing {listing_index}"
    
    async def _handle_open_chat(self, listing_index: int) -> str:
        """Handle open_chat tool."""
        if not self.current_listings:
            return "No listings available. Search first."
        
        if listing_index < 0 or listing_index >= len(self.current_listings):
            return f"Invalid listing index. Valid range: 0-{len(self.current_listings)-1}"
        
        listing = self.current_listings[listing_index]
        page = self.browser.get_page()
        
        if not page:
            return "Browser not ready"
        
        # First, navigate to the listing
        url = listing.get("listing_url")
        if url and page.url != url:
            await self.browser.navigate(url)
            await asyncio.sleep(2)
        
        # Try to find and click chat button
        chat_selectors = [
            '[data-testid="chat-button"]',
            'button:has-text("Chat")',
            'a:has-text("Chat")',
            '[class*="chat"]',
            'button:has-text("Make Offer")',
        ]
        
        for selector in chat_selectors:
            try:
                await page.click(selector, timeout=3000)
                await asyncio.sleep(1)
                return f"Opened chat for: {listing['title']}"
            except Exception:
                continue
        
        return f"Could not find chat button for listing {listing_index}. You may need to login first."
    
    async def _handle_delegate_lowball(self, listing_index: int) -> str:
        """Handle delegate_lowball tool with full navigation flow."""
        if not self.current_listings:
            return "No listings available. Search first."
        
        if listing_index < 0 or listing_index >= len(self.current_listings):
            return f"Invalid listing index. Valid range: 0-{len(self.current_listings)-1}"
        
        listing = self.current_listings[listing_index]
        page = self.browser.get_page()
        
        if not page:
            return "Browser not ready"
        
        # Step 1: Navigate to listing page to get details
        url = listing.get("listing_url")
        print(f"CONTROLLER: Navigating to listing: {listing['title']} (URL: {url})")
        if url:
            success = await self.browser.navigate(url)
            if not success:
                return f"Failed to navigate to listing URL: {url}"
            
            # Wait for the page to actually be a listing page (containing /p/)
            try:
                await page.wait_for_url(lambda u: "/p/" in u or "/listing/" in u, timeout=5000)
            except:
                print(f"CONTROLLER: Warning - Navigation timed out or URL doesn't look like a listing: {page.url}")
            
            await asyncio.sleep(2)
            
            # Step 2: Extract description and enriched details
            print("CONTROLLER: Reading listing description...")
            html = await page.content()
            details = extract_listing_details(html)
            listing.update(details)
            print(f"CONTROLLER: ✓ Description extracted ({len(listing.get('description', ''))} chars)")
        
        # Step 3: Open the chat
        print(f"CONTROLLER: Opening chat (Current URL: {page.url})...")
        chat_opened = False
        
        # Strategy 1: Explicit Role/Text logic (Most robust in Playwright)
        try:
            # Look for a button that has the text "Chat"
            btn = page.get_by_role("button", name=re.compile(r"^Chat$", re.I))
            if await btn.count() > 0 and await btn.first.is_visible():
                await btn.first.click()
                chat_opened = True
                print("CONTROLLER: ✓ Clicked 'Chat' button via role/text")
        except Exception: pass

        if not chat_opened:
            # Strategy 2: List of selectors
            chat_selectors = [
                'text="Chat"',
                '[data-testid="chat-button"]',
                'button:has-text("Chat")',
                'button:has-text("Chat with Seller")',
                'a:has-text("Chat")',
                'button:has-text("Buy Now")', 
                '[class*="chat"]',
                'button:has-text("Make Offer")',
                'button:has-text("Direct Message")',
            ]
            
            for selector in chat_selectors:
                try:
                    # Use wait_for_selector via browser_loader
                    btn = await page.wait_for_selector(selector, timeout=2000)
                    if btn and await btn.is_visible():
                        await btn.click()
                        chat_opened = True
                        print(f"CONTROLLER: ✓ Clicked chat button via selector ({selector})")
                        break
                except Exception:
                    continue
        
        if not chat_opened:
             # Take screenshot to see what went wrong
             await self.browser.screenshot("screenshots/chat_open_failed.png")
             return f"Could not find chat button on listing page. Please check the screenshot."

        # Wait for chat page to load
        await asyncio.sleep(4) 

        # Lazy-load lowballer
        if self.lowballer is None:
            from lowballer import LowballerAgent
            self.lowballer = LowballerAgent(self.llm)
        
        # Step 4: Delegate to lowballer
        print("CONTROLLER: Handing over to Lowballer Agent...")
        result = await self.lowballer.negotiate(
            listing_data=listing,
            page=page,
        )
        
        return result
    
    async def _handle_screenshot(self, filename: Optional[str] = None) -> str:
        """Handle take_screenshot tool."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshots/screenshot_{timestamp}.png"
        
        path = await self.browser.screenshot(filename)
        return f"Screenshot saved: {path}"


# Standalone test
if __name__ == "__main__":
    async def test_controller():
        print("=" * 50)
        print("CONTROLLER AGENT TEST")
        print("=" * 50)
        
        # Create mock browser and LLM
        llm = LLMFactory.from_env()
        browser = BrowserLoader(headless=False)
        
        # Launch browser
        await browser.launch()
        await browser.navigate("https://www.carousell.sg")
        
        # Create controller
        controller = ControllerAgent(llm, browser)
        
        # Test prompts
        test_prompts = [
            "Find iPhones under $3000",
            "Show me the listings",
        ]
        
        for prompt in test_prompts:
            print(f"\n>>> {prompt}")
            result = await controller.run(prompt)
            print(f"<<< {result}")
        
        # Keep browser open for inspection
        await asyncio.sleep(10)
        await browser.close()
    
    asyncio.run(test_controller())
