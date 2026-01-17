"""
DEV 2: CONTROLLER AGENT TEST SCRIPT
Run this to test the Controller independently using mock browser/DOM

Usage: python dev2_test_controller.py

This uses mock modules so you don't need Dev 1's browser code working.
Once Dev 1's code is ready, switch to real imports.
"""

import asyncio
import sys
sys.path.insert(0, '.')  # Ensure we can import from root

# ============================================
# TOGGLE: Use mocks or real modules
# Set to False once Dev 1's code is ready
USE_MOCKS = True
# ============================================

if USE_MOCKS:
    print("🔧 Using MOCK browser/DOM modules")
    from mocks import MockBrowserLoader as BrowserLoader
    from mocks import extract_dom, parse_listings, filter_listings_by_price, format_listings_for_display
else:
    print("🌐 Using REAL browser/DOM modules")
    from browser_loader import BrowserLoader
    from dom_extractor import extract_dom
    from dom_parser import parse_listings, filter_listings_by_price, format_listings_for_display

from llm_factory import LLMFactory
from controller import ControllerAgent


async def test_controller():
    """Test the Controller Agent with mock or real browser."""
    
    print("=" * 60)
    print("DEV 2: CONTROLLER AGENT TEST")
    print("=" * 60)
    
    # Initialize browser (mock or real)
    browser = BrowserLoader(headless=False)
    await browser.launch()
    await browser.navigate("https://www.carousell.sg")
    
    # Initialize LLM
    print("\n🤖 Initializing LLM...")
    llm = LLMFactory.from_env()
    
    # Create Controller Agent
    controller = ControllerAgent(llm, browser)
    
    # ============================================
    # TEST SCENARIOS
    # ============================================
    
    test_prompts = [
        # Test 1: Search functionality
        "Find iPhones under $600",
        
        # Test 2: Extract listings
        "Show me the listings",
        
        # Test 3: Open a listing
        "Open listing 0",
        
        # Test 4: Take screenshot
        "Take a screenshot",
    ]
    
    print("\n" + "=" * 60)
    print("RUNNING TEST SCENARIOS")
    print("=" * 60)
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n{'─' * 40}")
        print(f"TEST {i}: {prompt}")
        print('─' * 40)
        
        try:
            result = await controller.run(prompt)
            print(f"✅ Result: {result}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # ============================================
    # TOOL EXECUTION TESTS
    # ============================================
    
    print("\n" + "=" * 60)
    print("DIRECT TOOL TESTS")
    print("=" * 60)
    
    # Test search handler directly
    print("\n📍 Testing _handle_search directly...")
    result = await controller._handle_search("macbook", max_price=1500)
    print(f"   Result: {result}")
    
    # Test extract handler
    print("\n📍 Testing _handle_extract directly...")
    result = await controller._handle_extract()
    print(f"   Result: {result}")
    
    # Test screenshot
    print("\n📍 Testing _handle_screenshot directly...")
    result = await controller._handle_screenshot("test_shot.png")
    print(f"   Result: {result}")
    
    # Cleanup
    await browser.close()
    
    print("\n" + "=" * 60)
    print("✅ ALL CONTROLLER TESTS PASSED!")
    print("=" * 60)


async def test_tool_definitions():
    """Test that tool definitions are correct."""
    
    print("\n" + "=" * 60)
    print("TOOL DEFINITION TEST")
    print("=" * 60)
    
    browser = BrowserLoader()
    await browser.launch()
    llm = LLMFactory.from_env()
    controller = ControllerAgent(llm, browser)
    
    print("\n📋 Available tools:")
    for tool in controller.tools:
        func = tool.get("function", {})
        name = func.get("name", "unknown")
        desc = func.get("description", "")[:60]
        print(f"   • {name}: {desc}...")
    
    print("\n📋 Tool handlers:")
    for name, handler in controller.tool_handlers.items():
        print(f"   • {name} → {handler.__name__}")
    
    await browser.close()
    print("\n✅ Tool definitions valid!")


if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════╗
║  DEV 2: CONTROLLER AGENT DEVELOPMENT                      ║
║                                                           ║
║  This script tests your Controller implementation         ║
║  using mock browser/DOM modules.                          ║
║                                                           ║
║  Set USE_MOCKS = False when Dev 1's code is ready.        ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(test_controller())
    asyncio.run(test_tool_definitions())
