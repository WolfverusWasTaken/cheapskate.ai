"""
MODULE 1: Browser Loader (Dev 1)
Purpose: Launches persistent Playwright Chromium with visible browser (headless=False)

Provides:
- BrowserLoader.launch() → returns browser/context/page objects
- browser_loader.get_page() → shares page with other modules
- await browser_loader.navigate(url) → navigates to any URL
"""

import asyncio
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright


class BrowserLoader:
    """
    Manages a persistent Playwright Chromium browser instance.
    Designed to be shared across all agent modules.
    """
    
    def __init__(self, headless: bool = False):
        """
        Initialize the browser loader.
        
        Args:
            headless: Whether to run browser in headless mode (default: False for visible browser)
        """
        self.headless = headless
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._launched = False
        
    async def launch(self) -> tuple[Browser, BrowserContext, Page]:
        """
        Launch the Chromium browser with persistent context.
        
        Returns:
            Tuple of (browser, context, page) objects
        """
        if self._launched:
            print("BROWSER: Already launched, returning existing instances")
            return self._browser, self._context, self._page
            
        print(f"BROWSER: Launching Chromium (headless={self.headless})...")
        
        self._playwright = await async_playwright().start()
        
        # Launch with visible browser and reasonable viewport
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            slow_mo=100,  # Slight delay for visibility
            args=[
                '--start-maximized',
                '--disable-blink-features=AutomationControlled',
            ]
        )
        
        # Create context with realistic user agent
        self._context = await self._browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-SG',
            timezone_id='Asia/Singapore',
        )
        
        self._page = await self._context.new_page()
        self._launched = True
        
        print("BROWSER: ✓ Browser launched successfully")
        return self._browser, self._context, self._page
    
    def get_page(self) -> Optional[Page]:
        """
        Get the shared page instance.
        
        Returns:
            The current Page object or None if not launched
        """
        if not self._launched:
            print("BROWSER: Warning - Browser not launched yet")
            return None
        return self._page
    
    def get_context(self) -> Optional[BrowserContext]:
        """Get the browser context."""
        return self._context
    
    def get_browser(self) -> Optional[Browser]:
        """Get the browser instance."""
        return self._browser
    
    async def navigate(self, url: str, wait_until: str = "domcontentloaded") -> bool:
        """
        Navigate to a URL.
        
        Args:
            url: The URL to navigate to
            wait_until: When to consider navigation complete ('load', 'domcontentloaded', 'networkidle')
            
        Returns:
            True if navigation successful, False otherwise
        """
        if not self._page:
            print("BROWSER: Error - No page available. Call launch() first.")
            return False
            
        try:
            print(f"BROWSER: Navigating to {url}...")
            await self._page.goto(url, wait_until=wait_until, timeout=30000)
            print(f"BROWSER: ✓ Navigation complete → {self._page.url}")
            return True
        except Exception as e:
            print(f"BROWSER: ✗ Navigation failed → {e}")
            return False
    
    async def wait_for_selector(self, selector: str, timeout: int = 10000) -> bool:
        """
        Wait for a selector to appear on the page.
        
        Args:
            selector: CSS selector to wait for
            timeout: Maximum wait time in milliseconds
            
        Returns:
            True if element found, False otherwise
        """
        if not self._page:
            return False
            
        try:
            await self._page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception:
            return False
    
    async def screenshot(self, path: str = "screenshot.png") -> str:
        """
        Take a screenshot of the current page.
        
        Args:
            path: Path to save the screenshot
            
        Returns:
            Path to the saved screenshot
        """
        if not self._page:
            print("BROWSER: Error - No page available for screenshot")
            return ""
            
        await self._page.screenshot(path=path, full_page=False)
        print(f"BROWSER: ✓ Screenshot saved → {path}")
        return path
    
    async def close(self):
        """Close the browser and clean up resources."""
        print("BROWSER: Closing browser...")
        
        if self._page:
            await self._page.close()
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
            
        self._launched = False
        print("BROWSER: ✓ Browser closed")
    
    @property
    def is_launched(self) -> bool:
        """Check if browser is currently launched."""
        return self._launched


# Standalone test
if __name__ == "__main__":
    async def test_browser():
        print("=" * 50)
        print("BROWSER LOADER TEST")
        print("=" * 50)
        
        loader = BrowserLoader(headless=False)
        
        # Test launch
        browser, context, page = await loader.launch()
        assert browser is not None, "Browser should be launched"
        assert loader.is_launched, "Should be marked as launched"
        
        # Test navigation
        success = await loader.navigate("https://www.carousell.sg")
        assert success, "Navigation should succeed"
        
        # Test page access
        page = loader.get_page()
        assert page is not None, "Page should be accessible"
        print(f"BROWSER: Current URL → {page.url}")
        
        # Test screenshot
        path = await loader.screenshot("test_screenshot.png")
        assert path != "", "Screenshot should be saved"
        
        # Keep browser open for visual inspection
        print("\nBROWSER: Test complete! Browser will stay open for 5 seconds...")
        await asyncio.sleep(5)
        
        await loader.close()
        print("BROWSER: ✓ All tests passed!")
        
    asyncio.run(test_browser())
