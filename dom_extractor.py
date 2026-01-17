"""
MODULE 2: DOM Extractor (Dev 2)
Purpose: Converts browser page → structured JSON + screenshot

Provides:
- extract_dom(page) → returns dict with HTML, screenshot path, URL, timestamp
- Works with any Playwright page object
"""

import asyncio
from datetime import datetime
from typing import Optional
from pathlib import Path


async def extract_dom(page, screenshot_path: Optional[str] = None) -> dict:
    """
    Extract the full DOM and take a screenshot of the current page.
    
    Args:
        page: Playwright Page object
        screenshot_path: Custom path for screenshot (default: auto-generated)
        
    Returns:
        Dictionary containing:
        - html: Full outer HTML of the document
        - screenshot: Path to saved screenshot
        - url: Current page URL
        - timestamp: Extraction timestamp
        - title: Page title
    """
    if page is None:
        print("DOM_EXTRACTOR: Error - No page provided")
        return {
            "html": "",
            "screenshot": "",
            "url": "",
            "timestamp": datetime.now().isoformat(),
            "title": "",
            "error": "No page provided"
        }
    
    print("DOM_EXTRACTOR: Extracting DOM...")
    
    try:
        # Get full HTML
        html = await page.evaluate("document.documentElement.outerHTML")
        
        # Get page title
        title = await page.title()
        
        # Generate screenshot path if not provided
        if screenshot_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"screenshots/dom_{timestamp}.png"
        
        # Ensure screenshots directory exists
        Path(screenshot_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Take screenshot
        await page.screenshot(path=screenshot_path, full_page=False)
        
        result = {
            "html": html,
            "screenshot": screenshot_path,
            "url": page.url,
            "timestamp": datetime.now().isoformat(),
            "title": title,
        }
        
        print(f"DOM_EXTRACTOR: ✓ Extracted {len(html)} chars from {page.url}")
        print(f"DOM_EXTRACTOR: ✓ Screenshot saved → {screenshot_path}")
        
        return result
        
    except Exception as e:
        print(f"DOM_EXTRACTOR: ✗ Extraction failed → {e}")
        return {
            "html": "",
            "screenshot": "",
            "url": page.url if page else "",
            "timestamp": datetime.now().isoformat(),
            "title": "",
            "error": str(e)
        }


async def extract_visible_text(page) -> str:
    """
    Extract only visible text content from the page.
    
    Args:
        page: Playwright Page object
        
    Returns:
        String containing all visible text
    """
    if page is None:
        return ""
        
    try:
        # Get text content, excluding scripts and styles
        text = await page.evaluate("""
            () => {
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    {
                        acceptNode: function(node) {
                            const parent = node.parentElement;
                            if (!parent) return NodeFilter.FILTER_REJECT;
                            const tag = parent.tagName.toLowerCase();
                            if (['script', 'style', 'noscript'].includes(tag)) {
                                return NodeFilter.FILTER_REJECT;
                            }
                            const style = window.getComputedStyle(parent);
                            if (style.display === 'none' || style.visibility === 'hidden') {
                                return NodeFilter.FILTER_REJECT;
                            }
                            return NodeFilter.FILTER_ACCEPT;
                        }
                    }
                );
                
                let text = '';
                while (walker.nextNode()) {
                    const content = walker.currentNode.textContent.trim();
                    if (content) text += content + ' ';
                }
                return text;
            }
        """)
        return text.strip()
    except Exception as e:
        print(f"DOM_EXTRACTOR: ✗ Text extraction failed → {e}")
        return ""


async def extract_element_info(page, selector: str) -> list[dict]:
    """
    Extract information about elements matching a selector.
    
    Args:
        page: Playwright Page object
        selector: CSS selector to match
        
    Returns:
        List of dictionaries with element info
    """
    if page is None:
        return []
        
    try:
        elements = await page.evaluate(f"""
            (selector) => {{
                const elements = document.querySelectorAll(selector);
                return Array.from(elements).map((el, index) => ({{
                    index: index,
                    tagName: el.tagName.toLowerCase(),
                    text: el.textContent.trim().substring(0, 200),
                    href: el.href || '',
                    className: el.className,
                    id: el.id,
                    rect: el.getBoundingClientRect()
                }}));
            }}
        """, selector)
        return elements
    except Exception as e:
        print(f"DOM_EXTRACTOR: ✗ Element extraction failed → {e}")
        return []


# Standalone test with mock HTML
if __name__ == "__main__":
    import os
    
    # Test with mock data (no browser needed)
    print("=" * 50)
    print("DOM EXTRACTOR TEST (Mock Mode)")
    print("=" * 50)
    
    # Create a mock HTML sample
    mock_html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test Page</title></head>
    <body>
        <div class="listing">
            <h2>iPhone 14 Pro</h2>
            <span class="price">$800</span>
            <button class="chat-btn">Chat</button>
        </div>
        <div class="listing">
            <h2>iPhone 13</h2>
            <span class="price">$500</span>
            <button class="chat-btn">Chat</button>
        </div>
    </body>
    </html>
    """
    
    # Simulate extraction result
    mock_result = {
        "html": mock_html,
        "screenshot": "mock_screenshot.png",
        "url": "https://carousell.sg/search/iphone",
        "timestamp": datetime.now().isoformat(),
        "title": "Test Page"
    }
    
    print(f"DOM_EXTRACTOR: Mock extraction result:")
    print(f"  - HTML length: {len(mock_result['html'])} chars")
    print(f"  - URL: {mock_result['url']}")
    print(f"  - Title: {mock_result['title']}")
    print(f"  - Timestamp: {mock_result['timestamp']}")
    print(f"DOM_EXTRACTOR: ✓ Mock test passed!")
