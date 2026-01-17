"""
MOCK DOM MODULES
For Dev 2 (Controller) and Dev 3 (Lowballer) to test without real parsing

These simulate dom_extractor.py and dom_parser.py with fake data.
"""

from datetime import datetime


# ============================================
# MOCK DOM EXTRACTOR
# ============================================

async def extract_dom(page) -> dict:
    """
    Mock version of dom_extractor.extract_dom()
    Returns pre-built fake DOM data.
    """
    print("MOCK_DOM: Extracting DOM (mock mode)...")
    
    html = await page.evaluate("document.documentElement.outerHTML") if page else ""
    
    return {
        "html": html,
        "screenshot": "mock_screenshot.png",
        "url": page.url if page else "https://www.carousell.sg",
        "timestamp": datetime.now().isoformat(),
        "title": "Mock Carousell Page",
    }


# ============================================
# MOCK DOM PARSER
# ============================================

def get_mock_listings() -> list[dict]:
    """
    Get pre-defined mock listings for testing.
    Dev 2 and Dev 3 can use these for controller/lowballer tests.
    """
    return [
        {
            "index": 0,
            "title": "iPhone 14 Pro 256GB - Like New",
            "price": 1200.0,
            "price_raw": "S$1,200",
            "seller_name": "techseller88",
            "seller_url": "",
            "listing_url": "https://www.carousell.sg/p/iphone-14-pro-256gb-123456",
            "chat_selector": '[data-testid="chat-button"]',
            "image_url": "https://media.carousell.com/img1.jpg",
        },
        {
            "index": 1,
            "title": "iPhone 13 128GB Good Condition",
            "price": 650.0,
            "price_raw": "S$650",
            "seller_name": "mobilehub",
            "seller_url": "",
            "listing_url": "https://www.carousell.sg/p/iphone-13-128gb-654321",
            "chat_selector": '[data-testid="chat-button"]',
            "image_url": "https://media.carousell.com/img2.jpg",
        },
        {
            "index": 2,
            "title": "iPhone 12 Mini 64GB",
            "price": 400.0,
            "price_raw": "S$400",
            "seller_name": "dealzking",
            "seller_url": "",
            "listing_url": "https://www.carousell.sg/p/iphone-12-mini-789012",
            "chat_selector": '[data-testid="chat-button"]',
            "image_url": "https://media.carousell.com/img3.jpg",
        },
        {
            "index": 3,
            "title": "iPhone 14 128GB Purple",
            "price": 580.0,
            "price_raw": "S$580",
            "seller_name": "phonemaster",
            "seller_url": "",
            "listing_url": "https://www.carousell.sg/p/iphone-14-128gb-111222",
            "chat_selector": '[data-testid="chat-button"]',
            "image_url": "https://media.carousell.com/img4.jpg",
        },
        {
            "index": 4,
            "title": "iPhone SE 2022 64GB",
            "price": 350.0,
            "price_raw": "S$350",
            "seller_name": "budgetphones",
            "seller_url": "",
            "listing_url": "https://www.carousell.sg/p/iphone-se-2022-333444",
            "chat_selector": '[data-testid="chat-button"]',
            "image_url": "https://media.carousell.com/img5.jpg",
        },
    ]


def parse_listings(dom_data: dict) -> list[dict]:
    """
    Mock version of dom_parser.parse_listings()
    Returns pre-defined listings regardless of HTML content.
    """
    print("MOCK_DOM: Parsing listings (mock mode)...")
    listings = get_mock_listings()
    print(f"MOCK_DOM: ✓ Returning {len(listings)} mock listings")
    return listings


def filter_listings_by_price(listings: list[dict], max_price: float) -> list[dict]:
    """Filter mock listings by price."""
    filtered = [l for l in listings if 0 < l.get("price", 0) <= max_price]
    print(f"MOCK_DOM: Filtered to {len(filtered)} listings under ${max_price}")
    return filtered


def format_listings_for_display(listings: list[dict]) -> str:
    """Format listings for CLI display."""
    if not listings:
        return "No listings found."
    
    lines = ["=" * 60, f"Found {len(listings)} listings:", "=" * 60]
    
    for listing in listings:
        lines.append(
            f"[{listing['index']}] {listing['title']}\n"
            f"    💰 {listing['price_raw']} | 👤 {listing['seller_name']}\n"
            f"    🔗 {listing['listing_url'][:50]}..."
        )
        lines.append("-" * 60)
    
    return "\n".join(lines)


if __name__ == "__main__":
    print("=" * 50)
    print("MOCK DOM MODULE TEST")
    print("=" * 50)
    
    # Test mock listings
    listings = get_mock_listings()
    print(f"\n✓ Got {len(listings)} mock listings:")
    for l in listings:
        print(f"  [{l['index']}] {l['title']} - ${l['price']}")
    
    # Test filtering
    filtered = filter_listings_by_price(listings, 600)
    print(f"\n✓ Filtered to {len(filtered)} listings under $600")
    
    print("\n✓ Mock DOM test passed!")
