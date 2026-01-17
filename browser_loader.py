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
        self._stream_task: Optional[asyncio.Task] = None
        self._streaming = False
        self.pending_chat_action = False  # Flag for main loop to process
        
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
            
        # Use native window size in headful mode to avoid "flushed" layout issues
        context_kwargs = {
            "user_agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            "locale": 'en-SG',
            "timezone_id": 'Asia/Singapore',
            "storage_state": storage_state
        }
        
        if not self.headless:
            # Let the browser window dictate the size to avoid layout shifts
            context_kwargs["no_viewport"] = True
        else:
            # Fixed viewport for headless streaming
            context_kwargs["viewport"] = {'width': 1920, 'height': 1080}
            
        self._context = await self._browser.new_context(**context_kwargs)
        
        self._page = await self._context.new_page()
        
        # Apply manual stealth scripts to hide automation
        await self._apply_stealth(self._page)
        
        self._launched = True
    
    async def _apply_stealth(self, page: Page):
        """Apply stealth scripts to mask automation fingerprints."""
        stealth_js = """
        // Mask webdriver
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        
        // Mask plugins
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        
        // Mask languages
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        
        // Mask chrome property
        window.chrome = { runtime: {} };
        
        // Mask permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
        );
        """
        await page.add_init_script(stealth_js)
        print("BROWSER: 🛡️ Stealth mode applied")
        
        # Start streaming automatically if requested or as a standard feature
        await self.start_streaming()
        
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

    async def start_streaming(self):
        """Start the background live-stream task."""
        if self._stream_task is not None and not self._stream_task.done():
            return

        self._streaming = True
        self._stream_task = asyncio.create_task(self._streaming_loop())
        print("BROWSER: 📡 Live-stream bridge started (dashboard/public/live.jpg)")

    async def stop_streaming(self):
        """Stop the background live-stream task."""
        self._streaming = False
        if self._stream_task:
            self._stream_task.cancel()
            try:
                await self._stream_task
            except asyncio.CancelledError:
                pass
            self._stream_task = None
        print("BROWSER: 📡 Live-stream bridge stopped")

    async def _streaming_loop(self):
        # Use absolute paths for Windows reliability
        base_dir = os.path.dirname(os.path.abspath(__file__))
        public_dir = os.path.join(base_dir, "dashboard", "public")
        stream_path = os.path.join(public_dir, "live.jpg")
        temp_path = os.path.join(public_dir, "live.tmp.jpg")
        
        # Ensure directory exists
        os.makedirs(public_dir, exist_ok=True)
        
        print(f"BROWSER: 📡 Stream paths: {stream_path}")
        
        last_msg_check = 0
        last_idle_refresh = 0
        import random
        
        while self._streaming:
            if self._page and not self._page.is_closed():
                try:
                    # Take screenshot to a temp file first to prevent UI flickering
                    await self._page.screenshot(
                        path=temp_path,
                        type="jpeg",
                        quality=45,
                    )
                    
                    # Atomic move ensures the file is always "complete" when React reads it
                    if os.path.exists(temp_path):
                        try:
                            if os.path.exists(stream_path):
                                os.remove(stream_path)
                            os.rename(temp_path, stream_path)
                        except OSError:
                            pass
                        finally:
                            if os.path.exists(temp_path):
                                try: os.remove(temp_path)
                                except: pass
                except Exception as e:
                    if "Target closed" not in str(e):
                        print(f"BROWSER: ⚠️ Stream capture error: {e}")
                
                current_time = asyncio.get_event_loop().time()
                current_url = self._page.url.rstrip('/')
                is_home = current_url == "https://www.carousell.sg" or current_url == "https://carousell.sg"
                
                # Idle auto-refresh: Every 20-30 seconds when on homepage
                if is_home and not self.pending_chat_action:
                    if current_time - last_idle_refresh > 25 + random.randint(-5, 5):
                        last_idle_refresh = current_time
                        print("BROWSER: 🔄 Idle refresh...")
                        try:
                            await self._page.reload(wait_until="domcontentloaded")
                            await asyncio.sleep(0.5)
                            await self.handle_carousell_popups()
                        except:
                            pass
                
                # Message badge detection: Check every 5 seconds on homepage
                if current_time - last_msg_check > 5.0:
                    last_msg_check = current_time
                    try:
                        if is_home:
                            badge = await self._page.query_selector('a[aria-label="Inbox"] div.D_azt')
                            if badge and await badge.is_visible():
                                print("BROWSER: 💬 Auto-detected new message! Navigating to Inbox...")
                                await self._page.goto("https://www.carousell.sg/inbox/", wait_until="domcontentloaded")
                                await asyncio.sleep(1)
                                await self.handle_carousell_popups()
                                self.pending_chat_action = True
                    except:
                        pass
            
            # Target ~3 FPS for smoother visualization
            await asyncio.sleep(0.3)
    
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
            target_url = url
            await self._page.goto(url, wait_until=wait_until, timeout=30000)
            
            # Initial popup check (popups may appear immediately)
            await asyncio.sleep(0.3)
            await self.handle_carousell_popups()
            
            # If redirected away from search (e.g. to a landing page), go back
            if "carousell.sg/search" in target_url and "carousell.sg/search" not in self._page.url:
                print(f"BROWSER: 🔄 Detected redirect away from search! Going back...")
                await self._page.go_back()
                await asyncio.sleep(1)
                await self.handle_carousell_popups()
            
            print(f"BROWSER: ✓ Navigation complete → {self._page.url}")
            
            # CRITICAL: Dismiss popups BEFORE any other interactions
            # Popups appear after page load and block all interactions
            await asyncio.sleep(0.5)  # Wait for popup to appear
            await self.handle_carousell_popups()
            await asyncio.sleep(0.2)  # Brief wait after dismissal
            
            # Special handling for Carousell search pages: switch to "All" tab if on "Certified"
            # Only do this AFTER popup is dismissed
            if "carousell.sg/search" in self._page.url:
                await self.handle_carousell_tabs()
            
            # Optional: Inject HUD (disabled to prevent flickering)
            # await self.inject_agent_ui()
            
            return True
        except Exception as e:
            print(f"BROWSER: ✗ Navigation failed → {e}")
            return False

    async def handle_carousell_popups(self):
        """Aggressive popup dismissal: Wait for popup, find X, click immediately."""
        try:
            # Wait a moment for popup to appear
            await asyncio.sleep(0.3)
            
            # Check for popup via JavaScript
            has_overlay = await self._page.evaluate("""
                () => {
                    const dialogs = document.querySelectorAll('[role="dialog"]');
                    for (let d of dialogs) {
                        const style = window.getComputedStyle(d);
                        if (style.display !== 'none' && style.visibility !== 'hidden') return true;
                    }
                    return false;
                }
            """)
            
            if not has_overlay:
                return
            
            print("BROWSER: 🧹 Popup detected, attempting to close...")
            
            # Try JavaScript click first (most reliable)
            clicked = await self._page.evaluate("""
                () => {
                    const buttons = document.querySelectorAll('button, [role="button"]');
                    for (let btn of buttons) {
                        const style = window.getComputedStyle(btn);
                        if (style.display === 'none') continue;
                        
                        const text = (btn.innerText || '').trim().toLowerCase();
                        const ariaLabel = (btn.getAttribute('aria-label') || '').toLowerCase();
                        
                        // Check for close/dismiss buttons
                        if ((text === '×' || text === '✕' || text === '✖' || 
                             text === 'okay' || text === 'got it' || text === 'close' ||
                             ariaLabel === 'close' || ariaLabel.includes('close')) &&
                            !text.includes('continue') && !text.includes('next')) {
                            btn.click();
                            return true;
                        }
                    }
                    return false;
                }
            """)
            
            if clicked:
                print("BROWSER: ✓ Closed popup via JavaScript")
                await asyncio.sleep(0.2)
                return
            
            # Fallback: Try CSS selectors
            popup_selectors = [
                'button:has-text("Okay")',
                'button:has-text("Got it")',
                'button:has-text("Close")',
                'button:has-text("×")',
                'button:has-text("✕")',
                'button[aria-label="Close"]',
                'text="Okay"',
                'svg[aria-label="Close"]',
            ]
            
            for selector in popup_selectors:
                try:
                    btn = await self._page.query_selector(selector)
                    if btn and await btn.is_visible():
                        await btn.click()
                        print(f"BROWSER: ✓ Closed popup via selector: {selector}")
                        await asyncio.sleep(0.2)
                        return
                except:
                    continue
                    
        except Exception as e:
            print(f"BROWSER: ⚠️ Popup handling error: {e}")

    async def handle_carousell_tabs(self):
        """Detect and click the 'All' tab on search pages to bypass 'Certified' filter."""
        try:
            # CRITICAL: Dismiss popups first - they block tab interactions
            await self.handle_carousell_popups()
            
            # Short wait for any dynamic tab loaders
            await asyncio.sleep(1.5)
            
            # Check popup again before interacting (popups can appear late)
            await self.handle_carousell_popups()
            
            # First, check if we're on a page that has the "Certified" tab (which means "All" tab exists)
            certified_tab = await self._page.query_selector('text="Certified"')
            if not certified_tab:
                # No Certified tab means we don't need to switch
                return False
            
            # Now look for the "All" tab specifically using Playwright's get_by_role
            try:
                # Look for a tab element with exact text "All"
                all_tab = self._page.get_by_role("tab", name="All")
                if await all_tab.count() > 0 and await all_tab.first.is_visible():
                    print(f"BROWSER: 🔍 Found 'All' tab, switching to view all listings...")
                    await all_tab.first.click()
                    await asyncio.sleep(2)
                    return True
            except:
                pass
            
            # Fallback: look for exact text match in the tab bar area
            try:
                # Look for elements that have EXACTLY "All" as their text (not containing "All")
                all_elements = await self._page.query_selector_all('p, span, button, a')
                for elem in all_elements:
                    text = await elem.inner_text()
                    if text.strip() == "All":
                        # Check if it's in the upper part of the page (tab bar area)
                        box = await elem.bounding_box()
                        if box and box['y'] < 200:  # Tab bar is typically in top 200px
                            print(f"BROWSER: 🔍 Found 'All' tab (fallback), switching...")
                            await elem.click()
                            await asyncio.sleep(2)
                            return True
            except:
                pass
                
        except Exception as e:
            print(f"BROWSER: Error handling Carousell tabs: {e}")
        return False

    async def idle_refresh(self, interval: int = 7, max_refreshes: int = 10):
        """Go home and refresh periodically to stay idle but active."""
        print(f"BROWSER: 🏠 Going home and starting idle refresh (interval: {interval}s)...")
        await self.navigate("https://www.carousell.sg")
        
        for i in range(max_refreshes):
            wait_time = interval + (i % 3) # Slight variation (5-10s range)
            print(f"BROWSER: 😴 Sleeping for {wait_time}s... (Refresh {i+1}/{max_refreshes})")
            await asyncio.sleep(wait_time)
            
            print("BROWSER: 🔄 Refreshing page...")
            await self._page.reload(wait_until="domcontentloaded")
            await self.handle_carousell_popups()
            await self.inject_agent_ui()
            
        print("BROWSER: 🏁 Idle refresh period complete.")

    async def parse_inbox_messages(self) -> list[dict]:
        """
        Parses the current /inbox/ page to find unread messages.
        
        Returns:
            List of unread chat info: [{'seller': 'name', 'message': 'text', 'index': 0}]
        """
        if not self._page or "/inbox" not in self._page.url.lower():
            return []

        print("BROWSER: 📨 Parsing inbox for unread messages...")
        
        # Use JavaScript to parse the specific sibling structure mentioned by the user
        unread_chats = await self._page.evaluate("""
            () => {
                const results = [];
                // 1. Find the "Chats" header text
                const paragraphs = document.querySelectorAll('p');
                let chatsHeader = null;
                for (let p of paragraphs) {
                    if (p.innerText.trim() === 'Chats') {
                        chatsHeader = p;
                        break;
                    }
                }
                
                if (!chatsHeader) return [];

                // 2. Find the container (usually a parent or grandparent) 
                // In Carousell UI, the header is inside a div, and its sibling contains the chats
                const headerContainer = chatsHeader.closest('div.D_Fv') || chatsHeader.parentElement;
                const chatsContainer = headerContainer ? headerContainer.nextElementSibling : null;
                
                if (!chatsContainer) return [];

                // 3. Look for all divs with role="button" inside the container
                const chatItems = chatsContainer.querySelectorAll('div[role="button"]');
                
                chatItems.forEach((item, index) => {
                    // Check for unread marker: <div class="D_axN"><span class="D_axO">1</span></div>
                    const badge = item.querySelector('.D_axN, .D_axO');
                    const isUnread = !!badge;
                    
                    if (isUnread) {
                        const itemParagraphs = item.querySelectorAll('p');
                        // First p is usually seller name, second is a name, third is the message snippet
                        // alexigeorg33390 (Seller) -> alexi item (Product snippet title) -> message snippet
                        // Based on HTML provided:
                        // p[0]: alexigeorg33390 (Seller Name)
                        // p[1]: Message text
                        const sellerName = itemParagraphs[0]?.innerText || "Unknown";
                        const latestMsg = itemParagraphs[1]?.innerText || "";
                        
                        results.push({
                            index: index,
                            seller: sellerName,
                            message: latestMsg,
                            unread: true
                        });
                    }
                });
                return results;
            }
        """)
        
        if unread_chats:
            print(f"BROWSER: 🔔 Found {len(unread_chats)} unread chats!")
        else:
            print("BROWSER: No unread chats found.")
            
        return unread_chats

    async def check_for_new_messages(self, interval: int = 7, max_checks: int = 20) -> bool:
        """
        Stay on homepage, refresh periodically, and check for new message notifications.
        
        Returns:
            True if a new message badge was detected.
        """
        print(f"BROWSER: 👀 Starting message check loop (interval: {interval}s, max_checks: {max_checks})...")
        
        # Navigate to home first
        await self.navigate("https://www.carousell.sg")
        
        for i in range(max_checks):
            wait_time = interval + (i % 4) # Variation between interval and interval+3
            print(f"BROWSER: 😴 Sleeping for {wait_time}s... (Check {i+1}/{max_checks})")
            await asyncio.sleep(wait_time)
            
            print("BROWSER: 🔄 Refreshing page...")
            await self._page.reload(wait_until="domcontentloaded")
            await self.handle_carousell_popups()
            
            # Check for notification badge on the inbox icon
            try:
                badge = await self._page.query_selector('a[aria-label="Inbox"] div.D_azt span')
                if badge and await badge.is_visible():
                    text = await badge.inner_text()
                    if text and text.strip().isdigit() and int(text.strip()) > 0:
                        print(f"BROWSER: 💬 NEW MESSAGE DETECTED! Badge shows: {text}")
                        return True
            except:
                pass
            
            print("BROWSER: No new messages yet...")
        
        print("BROWSER: 🏁 Message check loop complete. No new messages found.")
        return False
    
    async def click_inbox_chat(self, index: int) -> bool:
        """
        Clicks on a chat in the inbox list by its index (0 is topmost).
        """
        if not self._page or "/inbox" not in self._page.url.lower():
            print("BROWSER: Error - Not on inbox page")
            return False
            
        print(f"BROWSER: Clicking chat at index {index} in the list...")
        try:
            # Use JavaScript to find the exact container and click the role="button" at that index
            await self._page.evaluate(f"""
                (idx) => {{
                    const paragraphs = document.querySelectorAll('p');
                    let chatsHeader = null;
                    for (let p of paragraphs) {{
                        if (p.innerText.trim() === 'Chats') {{
                            chatsHeader = p;
                            break;
                        }}
                    }}
                    if (!chatsHeader) return;
                    const headerContainer = chatsHeader.closest('div.D_Fv') || chatsHeader.parentElement;
                    const chatsContainer = headerContainer ? headerContainer.nextElementSibling : null;
                    if (!chatsContainer) return;
                    
                    const chatItems = chatsContainer.querySelectorAll('div[role="button"]');
                    if (chatItems[idx]) {{
                        chatItems[idx].click();
                        return true;
                    }}
                    return false;
                }}
            """, index)
            await asyncio.sleep(2)
            return True
        except Exception as e:
            print(f"BROWSER: Failed to click chat: {e}")
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
        """Check if the user is currently logged in by checking the homepage."""
        if not self._page:
            return False
            
        try:
            # Navigate to home to check login status
            current_url = self._page.url
            if "carousell.sg" not in current_url:
                await self.navigate("https://www.carousell.sg")
                await asyncio.sleep(2)
            
            # Check for logged-in indicators:
            # - Profile avatar/dropdown (logged in)
            # - "Login" or "Sign up" text/button (NOT logged in)
            login_button = await self._page.query_selector('a[href="/login/"], button:has-text("Login"), button:has-text("Log in")')
            
            if login_button:
                # Found login button = NOT logged in
                return False
            
            # Look for profile indicators
            profile_indicators = [
                'img[alt*="Profile"]',
                'img[alt*="Avatar"]',
                '[aria-label*="Profile"]',
                'a[href*="/u/"]',  # User profile links
            ]
            for selector in profile_indicators:
                el = await self._page.query_selector(selector)
                if el:
                    return True
            
            return False
        except Exception as e:
            print(f"BROWSER: Login check error: {e}")
            return False

    async def login(self, username, password):
        """Perform automated login."""
        if not self._page:
            return False
        
        print(f"BROWSER: 🔑 Attempting login for {username}...")
        await self.navigate("https://www.carousell.sg/login/")
        await asyncio.sleep(3)
        
        try:
            # Step 1: Click "Email, username or mobile" button to switch to email login
            print("BROWSER: Looking for 'Email, username or mobile' button...")
            email_login_selectors = [
                'button:has-text("Email, username or mobile")',
                'button:has-text("Email")',
                'button:has-text("email")',
                'div:has-text("Email, username or mobile")',
                '[data-testid*="email"]',
            ]
            
            clicked_email = False
            for selector in email_login_selectors:
                try:
                    btn = await self._page.wait_for_selector(selector, timeout=3000)
                    if btn:
                        await btn.click()
                        clicked_email = True
                        print(f"BROWSER: ✓ Clicked email login button")
                        await asyncio.sleep(1)
                        break
                except:
                    continue
            
            if not clicked_email:
                print("BROWSER: ⚠️ Could not find 'Email' button - trying direct input")
            
            # Step 2: Fill username/email field
            print("BROWSER: Entering credentials...")
            username_filled = False
            user_selectors = [
                'input[type="text"]',
                'input[type="email"]',
                'input[name="username"]',
                'input[name="email"]',
                'input[placeholder*="email"]',
                'input[placeholder*="Email"]',
                'input[placeholder*="username"]',
                'input[placeholder*="mobile"]',
            ]
            for selector in user_selectors:
                try:
                    el = await self._page.wait_for_selector(selector, timeout=3000)
                    if el:
                        await el.fill(username)
                        username_filled = True
                        print(f"BROWSER: ✓ Filled username")
                        break
                except: 
                    continue
            
            if not username_filled:
                print("BROWSER: ✗ Could not find username field")
                await self.screenshot("screenshots/login_error_username.png")
                return False
            
            # Step 3: Fill password field
            password_filled = False
            pass_selectors = [
                'input[type="password"]',
                'input[name="password"]',
                'input[placeholder*="password"]',
                'input[placeholder*="Password"]',
            ]
            for selector in pass_selectors:
                try:
                    el = await self._page.wait_for_selector(selector, timeout=3000)
                    if el:
                        await el.fill(password)
                        password_filled = True
                        print(f"BROWSER: ✓ Filled password")
                        break
                except: 
                    continue
            
            if not password_filled:
                print("BROWSER: ✗ Could not find password field")
                await self.screenshot("screenshots/login_error_password.png")
                return False
            
            # Step 4: Click login button
            await asyncio.sleep(0.5)
            submit_selectors = [
                'button[type="submit"]',
                'button:has-text("Log in")',
                'button:has-text("Login")',
                'button:has-text("Sign in")',
            ]
            clicked = False
            for selector in submit_selectors:
                try:
                    btn = await self._page.query_selector(selector)
                    if btn:
                        await btn.click()
                        clicked = True
                        print(f"BROWSER: ✓ Clicked login button")
                        break
                except: 
                    continue
            
            if not clicked:
                print("BROWSER: ✗ Could not find submit button")
                await self.screenshot("screenshots/login_error_submit.png")
                return False
            
            # Step 5: Wait for login to complete
            print("BROWSER: Login submitted, waiting for verification...")
            print("BROWSER: ⚠️  If you see a CAPTCHA, please solve it manually in the browser window.")
            
            # Wait up to 60 seconds for login to complete
            for i in range(60):
                await asyncio.sleep(1)
                current_url = self._page.url
                
                # If we navigated away from login page, success!
                if "/login" not in current_url:
                    print("BROWSER: ✓ Login successful!")
                    
                    # Save storage state for future sessions
                    os.makedirs("auth", exist_ok=True)
                    await self._context.storage_state(path="auth/state.json")
                    print("BROWSER: ✓ Session saved to auth/state.json")
                    return True
                
                # Show progress every 10 seconds
                if (i + 1) % 10 == 0:
                    print(f"BROWSER: Still waiting... ({i + 1}s) - solve CAPTCHA if present")
            
            print("BROWSER: ⚠️ Login verification timed out after 60s.")
            await self.screenshot("screenshots/login_timeout.png")
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
