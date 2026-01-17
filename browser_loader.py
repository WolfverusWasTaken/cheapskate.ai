"""
MODULE 1: Browser Loader (Dev 1)
Purpose: Launches persistent Playwright Chromium with visible browser (headless=False)

Provides:
- BrowserLoader.launch() → returns browser/context/page objects
- browser_loader.get_page() → shares page with other modules
- await browser_loader.navigate(url) → navigates to any URL
"""

import asyncio
import os
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
        
        # Try to load existing session if it exists
        auth_path = "auth/state.json"
        
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
        storage_state = auth_path if os.path.exists(auth_path) else None
        if storage_state:
            print(f"BROWSER: Loading session from {auth_path}")
            
        self._context = await self._browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-SG',
            timezone_id='Asia/Singapore',
            storage_state=storage_state
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
            
            # Inject Agent HUD
            await self.inject_agent_ui()
            
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

    async def inject_agent_ui(self):
        """Injects a glowing HUD to show the browser is under AI control."""
        if not self._page:
            return

        print("BROWSER: 🤖 Injecting Agent HUD...")
        
        hud_css = """
        @keyframes agentPulse {
            0% { box-shadow: inset 0 0 15px rgba(0, 200, 255, 0.4); }
            100% { box-shadow: inset 0 0 40px rgba(0, 200, 255, 0.7); }
        }
        #agent-hud-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            pointer-events: none;
            z-index: 2147483647;
            animation: agentPulse 2s infinite alternate ease-in-out;
            border: 4px solid rgba(0, 200, 255, 0.3);
            box-sizing: border-box;
        }
        #agent-badge {
            position: fixed;
            top: 10px;
            right: 20px;
            background: rgba(0, 20, 30, 0.85);
            color: #00d9ff;
            padding: 5px 12px;
            border-radius: 20px;
            font-family: 'Segoe UI', Roboto, sans-serif;
            font-size: 12px;
            font-weight: bold;
            letter-spacing: 1px;
            border: 1px solid #00d9ff;
            box-shadow: 0 0 10px rgba(0, 217, 255, 0.5);
            z-index: 2147483647;
            display: flex;
            align-items: center;
            gap: 6px;
            backdrop-filter: blur(4px);
        }
        .agent-dot {
            width: 8px;
            height: 8px;
            background: #00d9ff;
            border-radius: 50%;
            box-shadow: 0 0 8px #00d9ff;
            animation: blink 1s infinite;
        }
        @keyframes blink {
            50% { opacity: 0.3; }
        }
        """

        hud_js = f"""
        (() => {{
            if (document.getElementById('agent-hud-overlay')) return;
            
            const style = document.createElement('style');
            style.textContent = `{hud_css}`;
            document.head.appendChild(style);
            
            const hud = document.createElement('div');
            hud.id = 'agent-hud-overlay';
            
            const badge = document.createElement('div');
            badge.id = 'agent-badge';
            badge.innerHTML = '<span class="agent-dot"></span> LOWBALLER AGENT ACTIVE';
            
            document.body.appendChild(hud);
            document.body.appendChild(badge);
        }})();
        """
        
        try:
            await self._page.evaluate(hud_js)
        except Exception as e:
            print(f"BROWSER: HUD injection skipped (likely non-HTML page): {e}")

    async def is_logged_in(self) -> bool:
        """Check if the user is currently logged in."""
        if not self._page:
            return False
            
        try:
            # Look for profile dropdown or specific logged-in indicator
            # Carousell's profile dropdown usually has a specific testid or icon
            logged_in_element = await self._page.query_selector('[data-testid="nav-profile-dropdown"], a[href="/profile/"]')
            return logged_in_element is not None
        except:
            return False

    async def login(self, username, password):
        """Perform automated login."""
        if not self._page:
            return False
            
        if await self.is_logged_in():
            print("BROWSER: Already logged in")
            return True
            
        print(f"BROWSER: 🔑 Attempting login for {username}...")
        await self.navigate("https://www.carousell.sg/login")
        await asyncio.sleep(3)
        
        try:
            # Wait for login fields - Try multiple common selectors
            print("BROWSER: Entering credentials...")
            
            # Username/Email field
            user_selectors = ['input[name="username"]', 'input[name="email"]', '#username', '#email']
            for selector in user_selectors:
                try:
                    await self._page.wait_for_selector(selector, timeout=2000)
                    await self._page.fill(selector, username)
                    break
                except: continue
            
            # Password field
            pass_selectors = ['input[name="password"]', '#password']
            for selector in pass_selectors:
                try:
                    await self._page.wait_for_selector(selector, timeout=2000)
                    await self._page.fill(selector, password)
                    break
                except: continue
            
            # Click login button
            submit_selectors = ['button[type="submit"]', 'button:has-text("Login")', 'button:has-text("Log in")']
            for selector in submit_selectors:
                try:
                    await self._page.click(selector, timeout=2000)
                    break
                except: continue
            
            # Wait for navigation or profile element
            print("BROWSER: Login submitted, waiting for verification (check for manual CAPTCHA if needed)...")
            
            # Success indicator
            try:
                await self._page.wait_for_selector('[data-testid="nav-profile-dropdown"]', timeout=30000)
                print("BROWSER: ✓ Login successful!")
                
                # Save storage state for future sessions
                os.makedirs("auth", exist_ok=True)
                await self._context.storage_state(path="auth/state.json")
                return True
            except:
                print("BROWSER: ⚠️ Login verification timed out. You may need to solve a CAPTCHA manually.")
                return False
                
        except Exception as e:
            print(f"BROWSER: ✗ Login failed: {e}")
            await self.screenshot("screenshots/login_error.png")
            return False
    
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
