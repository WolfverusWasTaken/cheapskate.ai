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
        self._popup_check_task: Optional[asyncio.Task] = None  # Background popup checker
        
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
    
    # Popup Management
    
    async def dismiss_popups(self, grace_period: float = 0.3, max_attempts: int = 5) -> bool:
        """
        Aggressive popup dismissal: Wait for popup, find X button, click immediately.
        
        Args:
            grace_period: Wait time for popup to appear (default 0.3s)
            max_attempts: Maximum attempts to dismiss (default 5)
            
        Returns:
            True if popup was dismissed, False otherwise
        """
        page = self.browser.get_page()
        if not page:
            return False
        
        print("CONTROLLER: 🧹 Checking for popups...")
        
        # Wait for popup to appear
        if grace_period > 0:
            await asyncio.sleep(grace_period)
        
        for attempt in range(max_attempts):
            try:
                # Check if popup exists using JavaScript (more reliable)
                popup_info = await page.evaluate("""
                    () => {
                        // Find dialogs
                        const dialogs = document.querySelectorAll('[role="dialog"]');
                        for (let d of dialogs) {
                            const style = window.getComputedStyle(d);
                            if (style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0') {
                                return { found: true, type: 'dialog' };
                            }
                        }
                        
                        // Find high z-index overlays
                        const all = document.querySelectorAll('*');
                        for (let el of all) {
                            const style = window.getComputedStyle(el);
                            const zIndex = parseInt(style.zIndex) || 0;
                            if (zIndex >= 1000 && style.display !== 'none' && style.visibility !== 'hidden') {
                                const rect = el.getBoundingClientRect();
                                if (rect.width > window.innerWidth * 0.5 && rect.height > window.innerHeight * 0.5) {
                                    return { found: true, type: 'overlay', zIndex: zIndex };
                                }
                            }
                        }
                        
                        return { found: false };
                    }
                """)
                
                if not popup_info.get('found'):
                    if attempt == 0:
                        print("CONTROLLER: ✓ No popup detected")
                    return False  # No popup found
                
                print(f"CONTROLLER: 🔍 Popup detected (attempt {attempt + 1}/{max_attempts})")
                
                # Try multiple strategies to find and click X button
                x_selectors = [
                    'button:has-text("×")',
                    'button:has-text("✕")',
                    'button:has-text("✖")',
                    'button[aria-label="Close"]',
                    'button[aria-label="close"]',
                    'button[aria-label*="Close" i]',
                    'svg[aria-label="Close"]',
                    'svg[aria-label="close"]',
                    '[data-testid*="close" i]',
                    '[class*="close"][class*="button"]',
                    '[class*="CloseButton"]',
                ]
                
                # Strategy 1: Try Playwright locators
                for selector in x_selectors:
                    try:
                        locator = page.locator(selector).first
                        if await locator.is_visible(timeout=500):
                            await locator.click(timeout=1000)
                            print(f"CONTROLLER: ✓ Clicked X button via selector: {selector}")
                            await asyncio.sleep(0.2)  # Brief wait for popup to close
                            return True
                    except Exception as e:
                        continue
                
                # Strategy 2: JavaScript-based click (more reliable for dynamic content)
                clicked = await page.evaluate("""
                    () => {
                        // Find all buttons and check for X/close
                        const buttons = document.querySelectorAll('button, [role="button"], a, div[onclick], span[onclick]');
                        for (let btn of buttons) {
                            const style = window.getComputedStyle(btn);
                            if (style.display === 'none' || style.visibility === 'hidden') continue;
                            
                            const text = (btn.innerText || btn.textContent || '').trim();
                            const ariaLabel = (btn.getAttribute('aria-label') || '').toLowerCase();
                            const className = (btn.className || '').toLowerCase();
                            
                            // Check if it's an X button
                            if (text === '×' || text === '✕' || text === '✖' || 
                                ariaLabel === 'close' || ariaLabel.includes('close') ||
                                className.includes('close')) {
                                
                                // Skip if it's "continue" or "next"
                                if (text.toLowerCase().includes('continue') || 
                                    text.toLowerCase().includes('next') ||
                                    ariaLabel.includes('continue')) {
                                    continue;
                                }
                                
                                const rect = btn.getBoundingClientRect();
                                if (rect.width > 0 && rect.height > 0) {
                                    btn.click();
                                    return true;
                                }
                            }
                        }
                        
                        // Also check SVG icons
                        const svgs = document.querySelectorAll('svg');
                        for (let svg of svgs) {
                            const style = window.getComputedStyle(svg);
                            if (style.display === 'none') continue;
                            
                            const ariaLabel = (svg.getAttribute('aria-label') || '').toLowerCase();
                            const className = (svg.className?.baseVal || svg.className || '').toLowerCase();
                            
                            if (ariaLabel.includes('close') || className.includes('close')) {
                                const parent = svg.closest('button, [role="button"], a, div, span');
                                if (parent) {
                                    parent.click();
                                    return true;
                                }
                            }
                        }
                        
                        return false;
                    }
                """)
                
                if clicked:
                    print("CONTROLLER: ✓ Clicked X button via JavaScript")
                    await asyncio.sleep(0.2)
                    return True
                
                # Strategy 3: ESC key
                if attempt >= 2:  # Try ESC after a few attempts
                    try:
                        await page.keyboard.press("Escape")
                        await asyncio.sleep(0.2)
                        print("CONTROLLER: ✓ Pressed ESC key")
                        # Check if popup is gone
                        still_there = await page.evaluate("""
                            () => {
                                const dialogs = document.querySelectorAll('[role="dialog"]');
                                for (let d of dialogs) {
                                    const style = window.getComputedStyle(d);
                                    if (style.display !== 'none') return true;
                                }
                                return false;
                            }
                        """)
                        if not still_there:
                            return True
                    except Exception:
                        pass
                
                # Wait a bit before next attempt
                if attempt < max_attempts - 1:
                    await asyncio.sleep(0.3)
                    
            except Exception as e:
                print(f"CONTROLLER: ⚠️ Popup dismissal attempt {attempt + 1} error: {e}")
                if attempt < max_attempts - 1:
                    await asyncio.sleep(0.3)
        
        print("CONTROLLER: ⚠️ Failed to dismiss popup after all attempts")
        return False
    
    async def debug_popups(self) -> str:
        """
        Debug function to inspect what popups/overlays are currently on the page.
        Returns a detailed report of potential popups.
        """
        page = self.browser.get_page()
        if not page:
            return "Browser not ready"
        
        try:
            js_debug = """
            () => {
                const report = {
                    dialogs: [],
                    highZIndex: [],
                    closeButtons: [],
                    overlays: []
                };
                
                // Find dialogs
                const dialogs = document.querySelectorAll('[role="dialog"]');
                dialogs.forEach((d, i) => {
                    const style = window.getComputedStyle(d);
                    report.dialogs.push({
                        index: i,
                        visible: style.display !== 'none',
                        zIndex: style.zIndex,
                        className: d.className,
                        id: d.id
                    });
                });
                
                // Find high z-index elements
                const allElements = document.querySelectorAll('*');
                for (let el of allElements) {
                    const style = window.getComputedStyle(el);
                    const zIndex = parseInt(style.zIndex) || 0;
                    if (zIndex >= 1000 && style.display !== 'none') {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 100 && rect.height > 100) {
                            report.highZIndex.push({
                                tag: el.tagName,
                                zIndex: zIndex,
                                className: el.className.substring(0, 50),
                                id: el.id,
                                size: `${Math.round(rect.width)}x${Math.round(rect.height)}`
                            });
                        }
                    }
                }
                
                // Find potential close buttons
                const buttons = document.querySelectorAll('button, [role="button"]');
                buttons.forEach((btn, i) => {
                    const style = window.getComputedStyle(btn);
                    if (style.display !== 'none') {
                        const text = (btn.innerText || '').trim();
                        const ariaLabel = btn.getAttribute('aria-label') || '';
                        const className = btn.className || '';
                        if (text.toLowerCase().includes('close') || 
                            text === '×' || text === '✕' || text === '✖' ||
                            ariaLabel.toLowerCase().includes('close') ||
                            className.toLowerCase().includes('close')) {
                            report.closeButtons.push({
                                index: i,
                                text: text,
                                ariaLabel: ariaLabel,
                                className: className.substring(0, 50),
                                visible: style.display !== 'none'
                            });
                        }
                    }
                });
                
                // Find overlays/modals by class
                const overlaySelectors = [
                    '[class*="modal"]',
                    '[class*="overlay"]',
                    '[class*="popup"]',
                    '[class*="Modal"]',
                    '[class*="Overlay"]'
                ];
                
                overlaySelectors.forEach(selector => {
                    try {
                        const els = document.querySelectorAll(selector);
                        els.forEach(el => {
                            const style = window.getComputedStyle(el);
                            if (style.display !== 'none') {
                                report.overlays.push({
                                    selector: selector,
                                    className: el.className.substring(0, 50),
                                    id: el.id,
                                    zIndex: style.zIndex
                                });
                            }
                        });
                    } catch(e) {}
                });
                
                return report;
            }
            """
            
            result = await page.evaluate(js_debug)
            
            report_lines = ["=== POPUP DEBUG REPORT ==="]
            report_lines.append(f"Dialogs found: {len(result.dialogs)}")
            for d in result.dialogs:
                report_lines.append(f"  - Dialog {d.index}: visible={d.visible}, zIndex={d.zIndex}, class={d.className[:30]}")
            
            report_lines.append(f"\nHigh z-index elements (>=1000): {len(result.highZIndex)}")
            for z in result.highZIndex[:5]:  # Limit to first 5
                report_lines.append(f"  - {z.tag}: zIndex={z.zIndex}, size={z.size}, class={z.className}")
            
            report_lines.append(f"\nClose buttons found: {len(result.closeButtons)}")
            for cb in result.closeButtons[:10]:  # Limit to first 10
                report_lines.append(f"  - Text: '{cb.text}', ariaLabel: '{cb.ariaLabel}', visible: {cb.visible}")
            
            report_lines.append(f"\nOverlays found: {len(result.overlays)}")
            for ov in result.overlays[:5]:  # Limit to first 5
                report_lines.append(f"  - {ov.selector}: class={ov.className}, zIndex={ov.zIndex}")
            
            report = "\n".join(report_lines)
            print(report)
            return report
            
        except Exception as e:
            error_msg = f"Debug error: {e}"
            print(error_msg)
            return error_msg
    
    async def _start_popup_monitor(self, interval: float = 2.0):
        """
        Background task that periodically checks for and dismisses popups.
        
        Args:
            interval: Seconds between popup checks (default 2.0 for faster checks)
        """
        while True:
            try:
                result = await self.dismiss_popups(grace_period=0.1)  # Minimal grace period
                if result:
                    print("CONTROLLER: 🔔 Background popup monitor dismissed a popup")
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception:
                # Continue monitoring even if one check fails
                await asyncio.sleep(interval)
    
    def start_popup_monitoring(self, interval: float = 3.0):
        """
        Start background popup monitoring.
        
        Args:
            interval: Seconds between popup checks (default: 3.0)
        """
        if self._popup_check_task is None or self._popup_check_task.done():
            self._popup_check_task = asyncio.create_task(self._start_popup_monitor(interval))
            print(f"CONTROLLER: Started background popup monitoring (interval: {interval}s)")
    
    def stop_popup_monitoring(self):
        """Stop background popup monitoring."""
        if self._popup_check_task and not self._popup_check_task.done():
            self._popup_check_task.cancel()
            print("CONTROLLER: Stopped background popup monitoring")
    
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
        
        # Aggressively dismiss popups after navigation (they appear after page load)
        await self.dismiss_popups(grace_period=0.5, max_attempts=3)
        
        # Extract listings
        dom_data = await extract_dom(page)
        self.current_listings = parse_listings(dom_data)
        
        # Apply price filter if specified
        if max_price:
            self.current_listings = filter_listings_by_price(self.current_listings, max_price)
        
        return f"Found {len(self.current_listings)} listings for '{query}'" + (f" under ${max_price}" if max_price else "")
    
    async def _handle_extract(self) -> str:
        """Handle extract_listings tool."""
        # Dismiss any popups before extracting
        await self.dismiss_popups(grace_period=0.2)
        
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
        # Dismiss any popups before opening listing
        await self.dismiss_popups(grace_period=0.2)
        
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
            await asyncio.sleep(0.5)  # Wait for page load
            await self.dismiss_popups(grace_period=0.2)  # Check for popups after navigation
            return f"Opened listing: {listing['title']} (${listing['price']})"
        return f"Failed to open listing {listing_index}"
    
    async def _handle_open_chat(self, listing_index: int) -> str:
        """Handle open_chat tool."""
        # Dismiss any popups before opening chat
        await self.dismiss_popups(grace_period=0.2)
        
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
            await asyncio.sleep(1)
            await self.dismiss_popups(grace_period=0.2)  # Check for popups after navigation
        
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
        # Dismiss any popups before starting
        await self.dismiss_popups(grace_period=0.2)
        
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
            
            await asyncio.sleep(1)
            await self.dismiss_popups(grace_period=0.2)  # Check for popups after navigation
            
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

        # Wait for chat page to load and check for popups
        await asyncio.sleep(2)
        await self.dismiss_popups(grace_period=0.2)  # Check for popups after opening chat 

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
        
        # Start background popup monitoring
        controller.start_popup_monitoring(interval=2.0)
        
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
        
        # Stop popup monitoring before closing
        controller.stop_popup_monitoring()
        await browser.close()
    
    asyncio.run(test_controller())
