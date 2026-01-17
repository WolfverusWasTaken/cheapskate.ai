"""
DEV 1: BROWSER & PARSING TEST SCRIPT
Run this to test browser_loader, dom_extractor, and dom_parser

Usage: python dev1_test_browser.py

This is YOUR code - test it with a real browser.
"""

import asyncio
import sys
sys.path.insert(0, '.')

from browser_loader import BrowserLoader
from dom_extractor import extract_dom, extract_visible_text
from dom_parser import parse_listings, filter_listings_by_price, format_listings_for_display
from config import config



async def ensure_login(browser):
    """Helper to login if credentials are set in .env."""
    if config.agent.username and config.agent.password:
        if not await browser.is_logged_in():
            print("🔑 Auto-login triggered...")
            await browser.login(config.agent.username, config.agent.password)
        else:
            print("✅ Already logged in (session restored)")


async def test_browser_loader():
    """Test the BrowserLoader module."""
    
    print("=" * 60)
    print("DEV 1: BROWSER LOADER TEST")
    print("=" * 60)
    
    # Initialize
    loader = BrowserLoader(headless=False)  # Visible browser
    
    # Test launch
    print("\n📍 Testing launch()...")
    browser, context, page = await loader.launch()
    assert loader.is_launched, "Browser should be launched"
    print("   ✅ Browser launched")
    
    # Auto-login
    await ensure_login(loader)
    
    # Test navigation
    print("\n📍 Testing navigate()...")
    success = await loader.navigate("https://www.carousell.sg")
    assert success, "Navigation should succeed"
    print(f"   ✅ Navigated to {loader.get_page().url}")
    
    # Wait for page to load
    await asyncio.sleep(2)
    
    # Test get_page
    print("\n📍 Testing get_page()...")
    page = loader.get_page()
    assert page is not None, "Page should exist"
    print(f"   ✅ Got page: {page.url}")
    
    # Test screenshot
    print("\n📍 Testing screenshot()...")
    path = await loader.screenshot("screenshots/dev1_test.png")
    print(f"   ✅ Screenshot saved: {path}")
    
    # Test search navigation
    print("\n📍 Testing search navigation...")
    await loader.navigate("https://www.carousell.sg/search/iphone")
    await asyncio.sleep(2)
    print(f"   ✅ Search URL: {loader.get_page().url}")
    
    # Keep browser open for inspection
    print("\n⏳ Browser open for 5 seconds for inspection...")
    await asyncio.sleep(5)
    
    # Cleanup
    await loader.close()
    print("\n✅ Browser loader test passed!")
    
    return True


async def test_dom_extractor():
    """Test the DOM Extractor module."""
    
    print("\n" + "=" * 60)
    print("DEV 1: DOM EXTRACTOR TEST")
    print("=" * 60)
    
    # Launch browser
    loader = BrowserLoader(headless=False)
    await loader.launch()
    await loader.navigate("https://www.carousell.sg/search/iphone")
    await asyncio.sleep(3)  # Wait for content
    
    page = loader.get_page()
    
    # Test extract_dom
    print("\n📍 Testing extract_dom()...")
    dom_data = await extract_dom(page)
    
    print(f"   HTML length: {len(dom_data.get('html', ''))} chars")
    print(f"   URL: {dom_data.get('url')}")
    print(f"   Title: {dom_data.get('title')}")
    print(f"   Screenshot: {dom_data.get('screenshot')}")
    print(f"   Timestamp: {dom_data.get('timestamp')}")
    
    assert len(dom_data.get('html', '')) > 1000, "Should get substantial HTML"
    print("   ✅ DOM extraction successful")
    
    # Test extract_visible_text
    print("\n📍 Testing extract_visible_text()...")
    text = await extract_visible_text(page)
    print(f"   Text length: {len(text)} chars")
    print(f"   Preview: {text[:200]}...")
    print("   ✅ Text extraction successful")
    
    await loader.close()
    return dom_data


async def test_dom_parser(dom_data: dict = None):
    """Test the DOM Parser module."""
    
    print("\n" + "=" * 60)
    print("DEV 1: DOM PARSER TEST")
    print("=" * 60)
    
    # If no dom_data provided, get fresh data
    if dom_data is None:
        loader = BrowserLoader(headless=False)
        await loader.launch()
        await loader.navigate("https://www.carousell.sg/search/iphone")
        await asyncio.sleep(3)
        dom_data = await extract_dom(loader.get_page())
        await loader.close()
    
    # Test parse_listings
    print("\n📍 Testing parse_listings()...")
    listings = parse_listings(dom_data)
    print(f"   Found {len(listings)} listings")
    
    if listings:
        print("\n   Sample listings:")
        for l in listings[:3]:
            print(f"   [{l['index']}] {l['title'][:40]}... - {l['price_raw']}")
    
    # Test filter
    print("\n📍 Testing filter_listings_by_price()...")
    filtered = filter_listings_by_price(listings, 3000)
    print(f"   Listings under $3000: {len(filtered)}")
    
    # Test display formatting
    print("\n📍 Testing format_listings_for_display()...")
    display = format_listings_for_display(listings[:2])
    print(display)
    
    print("\n✅ DOM parser test passed!")
    return listings


async def full_integration_test():
    """Run a full integration test of browser → extract → parse."""
    
    print("\n" + "=" * 60)
    print("DEV 1: FULL INTEGRATION TEST")
    print("=" * 60)
    
    loader = BrowserLoader(headless=False)
    
    try:
        # Step 1: Launch
        print("\n[1/4] Launching browser...")
        await loader.launch()
        
        # Auto-login
        await ensure_login(loader)
        
        # Step 2: Navigate to search
        print("[2/4] Navigating to Carousell search...")
        await loader.navigate("https://www.carousell.sg/search/iphone%2014")
        await asyncio.sleep(3)
        
        # Step 3: Extract DOM
        print("[3/4] Extracting DOM...")
        page = loader.get_page()
        dom_data = await extract_dom(page, "screenshots/integration_test.png")
        
        # Step 4: Parse listings
        print("[4/4] Parsing listings...")
        listings = parse_listings(dom_data)
        
        # Report
        print("\n" + "─" * 40)
        print("INTEGRATION TEST RESULTS")
        print("─" * 40)
        print(f"✅ Browser URL: {page.url}")
        print(f"✅ HTML extracted: {len(dom_data['html'])} chars")
        print(f"✅ Listings found: {len(listings)}")
        
        if listings:
            print("\n📦 Extracted Listings:")
            print(format_listings_for_display(listings[:5]))
        
        # Keep open for inspection
        print("\n⏳ Keeping browser open for 10 seconds...")
        await asyncio.sleep(10)
        
    finally:
        await loader.close()
    
    print("\n🎉 INTEGRATION TEST COMPLETE!")


if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════╗
║  DEV 1: BROWSER & PARSING DEVELOPMENT                     ║
║                                                           ║
║  Your modules:                                            ║
║  • browser_loader.py - Browser automation                 ║
║  • dom_extractor.py  - DOM capture + screenshots          ║
║  • dom_parser.py     - Carousell listing extraction       ║
║                                                           ║
║  Run this to test your implementations.                   ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--full', action='store_true', help='Run full integration test')
    parser.add_argument('--browser', action='store_true', help='Test browser only')
    parser.add_argument('--extractor', action='store_true', help='Test extractor only')
    parser.add_argument('--parser', action='store_true', help='Test parser only')
    args = parser.parse_args()
    
    if args.browser:
        asyncio.run(test_browser_loader())
    elif args.extractor:
        asyncio.run(test_dom_extractor())
    elif args.parser:
        asyncio.run(test_dom_parser())
    elif args.full:
        asyncio.run(full_integration_test())
    else:
        # Run all
        asyncio.run(test_browser_loader())
        asyncio.run(test_dom_extractor())
        asyncio.run(test_dom_parser())
        asyncio.run(full_integration_test())
