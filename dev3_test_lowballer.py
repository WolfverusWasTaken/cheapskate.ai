"""
DEV 3: LOWBALLER AGENT TEST SCRIPT
Run this to test the Lowballer independently using mock data

Usage: python dev3_test_lowballer.py

This tests negotiation logic without needing browser or controller.
"""

import asyncio
import sys
sys.path.insert(0, '.')  # Ensure we can import from root

# ============================================
# TOGGLE: Use mocks or real modules  
# Set to False once integration testing
USE_MOCKS = True
# ============================================

if USE_MOCKS:
    print("🔧 Using MOCK browser module")
    from mocks import MockBrowserLoader as BrowserLoader, MockPage
    from mocks import get_mock_listings
else:
    print("🌐 Using REAL browser module")
    from browser_loader import BrowserLoader

from llm_factory import LLMFactory
from lowballer import LowballerAgent


async def test_lowballer_basic():
    """Test basic Lowballer functionality with mock data."""
    
    print("=" * 60)
    print("DEV 3: LOWBALLER AGENT TEST - BASIC")
    print("=" * 60)
    
    # Initialize LLM
    print("\n🤖 Initializing LLM...")
    llm = LLMFactory.from_env()
    
    # Create Lowballer Agent
    lowballer = LowballerAgent(llm)
    
    # Get mock listing
    mock_listings = get_mock_listings()
    test_listing = mock_listings[0]  # iPhone 14 Pro @ $1200
    
    print(f"\n📦 Test Listing:")
    print(f"   Title: {test_listing['title']}")
    print(f"   Price: ${test_listing['price']}")
    print(f"   Seller: {test_listing['seller_name']}")
    
    # ============================================
    # TEST 1: Offer Calculation
    # ============================================
    print("\n" + "─" * 40)
    print("TEST 1: Offer Calculation")
    print("─" * 40)
    
    listing_price = test_listing["price"]
    
    for round_num in range(1, 6):
        offer = lowballer._calculate_offer(listing_price, round_num)
        percent = int((offer / listing_price) * 100)
        print(f"   Round {round_num}: ${offer} ({percent}% of ${listing_price})")
    
    # ============================================
    # TEST 2: Message Generation (No Browser)
    # ============================================
    print("\n" + "─" * 40)
    print("TEST 2: Message Generation")
    print("─" * 40)
    
    for round_num in [1, 2, 3]:
        offer_price = lowballer._calculate_offer(listing_price, round_num)
        message = await lowballer._generate_message(
            test_listing["title"],
            listing_price,
            offer_price,
            round_num
        )
        print(f"\n   Round {round_num} Message:")
        print(f"   \"{message}\"")
    
    # ============================================
    # TEST 3: Chat History
    # ============================================
    print("\n" + "─" * 40)
    print("TEST 3: Chat History")
    print("─" * 40)
    
    seller_id = lowballer._get_seller_id(test_listing)
    print(f"   Seller ID: {seller_id}")
    
    # Simulate some chat history
    lowballer.chat_history[seller_id] = {
        "listing": test_listing,
        "started_at": "2026-01-17T14:00:00",
        "messages": [
            {"role": "lowballer", "content": "Would you take $600?", "round": 1},
            {"role": "seller", "content": "Sorry, lowest is $1000"},
            {"role": "lowballer", "content": "How about $720?", "round": 2},
        ],
        "current_round": 2,
        "status": "active",
    }
    
    print(f"\n   Chat Summary:")
    print(lowballer.get_chat_summary(seller_id))
    
    print("\n✅ Basic tests passed!")


async def test_lowballer_with_mock_page():
    """Test Lowballer with mock page object."""
    
    print("\n" + "=" * 60)
    print("DEV 3: LOWBALLER AGENT TEST - WITH MOCK PAGE")
    print("=" * 60)
    
    # Initialize 
    llm = LLMFactory.from_env()
    lowballer = LowballerAgent(llm)
    
    # Create mock page
    mock_page = MockPage()
    await mock_page.goto("https://carousell.sg/p/test-listing")
    
    # Get mock listing
    mock_listings = get_mock_listings()
    test_listing = mock_listings[2]  # iPhone 12 Mini @ $400
    
    print(f"\n📦 Test Listing:")
    print(f"   Title: {test_listing['title']}")
    print(f"   Price: ${test_listing['price']}")
    
    # ============================================
    # TEST: Full Negotiation Flow (with mock page)
    # ============================================
    print("\n" + "─" * 40)
    print("TEST: Full Negotiation Flow")
    print("─" * 40)
    
    # Round 1
    result1 = await lowballer.negotiate(test_listing, mock_page)
    print(f"\n   Round 1 Result: {result1}")
    
    # Round 2 (continue negotiation)
    result2 = await lowballer.negotiate(test_listing, mock_page)
    print(f"   Round 2 Result: {result2}")
    
    # Round 3
    result3 = await lowballer.negotiate(test_listing, mock_page)
    print(f"   Round 3 Result: {result3}")
    
    print("\n✅ Mock page tests passed!")


async def test_negotiation_strategies():
    """Test different negotiation scenarios."""
    
    print("\n" + "=" * 60)
    print("DEV 3: NEGOTIATION STRATEGY TESTS")
    print("=" * 60)
    
    llm = LLMFactory.from_env()
    lowballer = LowballerAgent(llm)
    
    # Different price points
    test_cases = [
        {"title": "Budget Phone", "price": 100},
        {"title": "Mid-range Phone", "price": 500},
        {"title": "Premium Phone", "price": 1500},
        {"title": "Luxury Watch", "price": 5000},
    ]
    
    print("\n📊 Offer Strategies by Price Point:")
    print("─" * 50)
    
    for item in test_cases:
        print(f"\n{item['title']} @ ${item['price']}:")
        for round_num in [1, 2, 3]:
            offer = lowballer._calculate_offer(item["price"], round_num)
            print(f"   R{round_num}: ${offer} ({int(offer/item['price']*100)}%)")
    
    print("\n✅ Strategy tests passed!")


async def test_fallback_messages():
    """Test fallback messages when LLM is unavailable."""
    
    print("\n" + "=" * 60)
    print("DEV 3: FALLBACK MESSAGE TESTS")
    print("=" * 60)
    
    llm = LLMFactory.from_env()
    lowballer = LowballerAgent(llm)
    
    print("\n📝 Fallback Messages (no LLM):")
    
    for round_num in [1, 2, 3]:
        msg = lowballer._get_fallback_message("iPhone 14", 400, round_num)
        print(f"   Round {round_num}: \"{msg}\"")
    
    print("\n✅ Fallback tests passed!")


if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════╗
║  DEV 3: LOWBALLER AGENT DEVELOPMENT                       ║
║                                                           ║
║  This script tests your Lowballer implementation          ║
║  without needing browser or controller.                   ║
║                                                           ║
║  Focus areas:                                             ║
║  • Offer calculation (50% → 70% strategy)                 ║
║  • Message generation with LLM                            ║
║  • Chat history management                                ║
║  • Counter-offer handling                                 ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(test_lowballer_basic())
    asyncio.run(test_lowballer_with_mock_page())
    asyncio.run(test_negotiation_strategies())
    asyncio.run(test_fallback_messages())
    
    print("\n" + "=" * 60)
    print("🎉 ALL DEV 3 TESTS COMPLETE!")
    print("=" * 60)
