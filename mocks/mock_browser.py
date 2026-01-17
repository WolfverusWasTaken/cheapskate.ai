"""
MOCK BROWSER MODULE
For Dev 2 (Controller) and Dev 3 (Lowballer) to test without real browser

This simulates the browser_loader.py interface with fake responses.
Replace with real browser_loader when Dev 1's code is ready.
"""

import asyncio
from typing import Optional, Any
from datetime import datetime


class MockPage:
    """Mock Playwright page for testing."""
    
    def __init__(self):
        self.url = "https://www.carousell.sg"
        self._current_html = self._get_mock_search_html()
    
    async def goto(self, url: str, **kwargs):
        """Simulate navigation."""
        self.url = url
        print(f"MOCK_BROWSER: Navigated to {url}")
        
        if "search" in url:
            self._current_html = self._get_mock_search_html()
        elif "/p/" in url:
            self._current_html = self._get_mock_listing_html()
        
        return True
    
    async def evaluate(self, script: str):
        """Simulate JavaScript evaluation."""
        if "outerHTML" in script:
            return self._current_html
        return ""
    
    async def title(self):
        return "Mock Carousell Page"
    
    async def screenshot(self, **kwargs):
        path = kwargs.get("path", "mock_screenshot.png")
        print(f"MOCK_BROWSER: Screenshot saved to {path}")
        return path
    
    async def click(self, selector: str, **kwargs):
        """Simulate clicking."""
        print(f"MOCK_BROWSER: Clicked {selector}")
        return True
    
    async def fill(self, selector: str, text: str):
        """Simulate typing."""
        print(f"MOCK_BROWSER: Typed '{text}' into {selector}")
        return True
    
    async def press(self, selector: str, key: str):
        """Simulate key press."""
        print(f"MOCK_BROWSER: Pressed {key} in {selector}")
        return True
    
    async def wait_for_selector(self, selector: str, **kwargs):
        """Simulate waiting for element."""
        return True
    
    def _get_mock_search_html(self) -> str:
        """Return mock Carousell search results HTML."""
        return """
        <!DOCTYPE html>
        <html>
        <head><title>iPhone - Carousell Singapore</title></head>
        <body>
            <div data-testid="listing-card-1" class="listing-card">
                <a href="/p/iphone-14-pro-256gb-123456">
                    <img src="https://media.carousell.com/img1.jpg" />
                    <h3 class="title">iPhone 14 Pro 256GB - Like New</h3>
                    <span class="price">S$1,200</span>
                    <span class="seller">techseller88</span>
                </a>
            </div>
            
            <div data-testid="listing-card-2" class="listing-card">
                <a href="/p/iphone-13-128gb-654321">
                    <img src="https://media.carousell.com/img2.jpg" />
                    <h3 class="title">iPhone 13 128GB Good Condition</h3>
                    <span class="price">S$650</span>
                    <span class="seller">mobilehub</span>
                </a>
            </div>
            
            <div data-testid="listing-card-3" class="listing-card">
                <a href="/p/iphone-12-mini-789012">
                    <img src="https://media.carousell.com/img3.jpg" />
                    <h3 class="title">iPhone 12 Mini 64GB</h3>
                    <span class="price">S$400</span>
                    <span class="seller">dealzking</span>
                </a>
            </div>
            
            <div data-testid="listing-card-4" class="listing-card">
                <a href="/p/iphone-14-128gb-111222">
                    <img src="https://media.carousell.com/img4.jpg" />
                    <h3 class="title">iPhone 14 128GB Purple</h3>
                    <span class="price">S$580</span>
                    <span class="seller">phonemaster</span>
                </a>
            </div>
            
            <div data-testid="listing-card-5" class="listing-card">
                <a href="/p/iphone-se-2022-333444">
                    <img src="https://media.carousell.com/img5.jpg" />
                    <h3 class="title">iPhone SE 2022 64GB</h3>
                    <span class="price">S$350</span>
                    <span class="seller">budgetphones</span>
                </a>
            </div>
        </body>
        </html>
        """
    
    def _get_mock_listing_html(self) -> str:
        """Return mock Carousell listing detail HTML."""
        return """
        <!DOCTYPE html>
        <html>
        <head><title>iPhone 14 Pro 256GB - Carousell</title></head>
        <body>
            <div class="listing-detail">
                <h1>iPhone 14 Pro 256GB - Like New</h1>
                <span class="price">S$1,200</span>
                <span class="seller">techseller88</span>
                <button data-testid="chat-button">Chat</button>
                <div class="description">
                    Selling my iPhone 14 Pro. Used for 6 months.
                    Battery health 97%. No scratches.
                </div>
            </div>
            <div class="chat-window">
                <textarea placeholder="Type message..."></textarea>
                <button type="submit">Send</button>
            </div>
        </body>
        </html>
        """


class MockBrowserLoader:
    """
    Mock version of BrowserLoader for testing.
    Provides the same interface as the real browser_loader.py
    """
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self._page: Optional[MockPage] = None
        self._launched = False
        print(f"MOCK_BROWSER: Initialized (headless={headless})")
    
    async def launch(self):
        """Simulate launching browser."""
        print("MOCK_BROWSER: Launching mock browser...")
        self._page = MockPage()
        self._launched = True
        print("MOCK_BROWSER: ✓ Mock browser ready")
        return None, None, self._page
    
    def get_page(self) -> Optional[MockPage]:
        """Get the mock page."""
        return self._page
    
    async def navigate(self, url: str, **kwargs) -> bool:
        """Simulate navigation."""
        if self._page:
            await self._page.goto(url)
            return True
        return False
    
    async def screenshot(self, path: str = "screenshot.png") -> str:
        """Simulate screenshot."""
        if self._page:
            return await self._page.screenshot(path=path)
        return ""
    
    async def close(self):
        """Simulate closing browser."""
        print("MOCK_BROWSER: Closing mock browser")
        self._launched = False
    
    @property
    def is_launched(self) -> bool:
        return self._launched


# Provide same name as real module for easy switching
BrowserLoader = MockBrowserLoader


if __name__ == "__main__":
    async def test():
        print("=" * 50)
        print("MOCK BROWSER TEST")
        print("=" * 50)
        
        loader = MockBrowserLoader()
        await loader.launch()
        
        await loader.navigate("https://www.carousell.sg/search/iphone")
        
        page = loader.get_page()
        html = await page.evaluate("document.documentElement.outerHTML")
        print(f"\n✓ Got {len(html)} chars of mock HTML")
        
        await loader.close()
        print("\n✓ Mock browser test passed!")
    
    asyncio.run(test())
