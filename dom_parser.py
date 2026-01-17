"""
MODULE 3: DOM Parser (Dev 2)
Purpose: Parses Carousell DOM → extracts actionable listings

Provides:
- parse_listings(dom_data) → returns list of listing dicts with title, price, seller, chat_selector
- Specialized for Carousell.sg HTML structure
"""

import re
from typing import Optional
from bs4 import BeautifulSoup
from pydantic import BaseModel


class CarousellListing(BaseModel):
    """Structured representation of a Carousell listing."""
    index: int
    title: str
    price: float
    price_raw: str
    seller_name: str
    seller_url: str
    listing_url: str
    chat_selector: str
    image_url: str = ""
    condition: str = ""
    location: str = ""


def parse_price(price_str: str) -> float:
    """
    Parse a price string to float, handling cases like "From S$538" or "$1,200".
    
    Args:
        price_str: Price string
        
    Returns:
        Float price value or 0.0 if failed
    """
    if not price_str:
        return 0.0
        
    # Extract only the currency-related part (digits, commas, dots)
    # We look for the first occurrence of $ followed by numbers, or just numbers
    match = re.search(r'[\d,]+(?:\.\d{1,2})?', price_str)
    if not match:
        return 0.0
        
    price_num_str = match.group().replace(',', '')
    try:
        return float(price_num_str)
    except ValueError:
        return 0.0


def parse_listings(dom_data: dict) -> list[dict]:
    """
    Parse Carousell DOM to extract listing information.
    
    Args:
        dom_data: Dictionary containing 'html' key with page HTML
        
    Returns:
        List of listing dictionaries with actionable information
    """
    html = dom_data.get("html", "")
    if not html:
        print("DOM_PARSER: Error - No HTML provided")
        return []
    
    print("DOM_PARSER: Parsing Carousell listings...")
    
    soup = BeautifulSoup(html, 'html.parser')
    listings = []
    
    # Carousell uses various container patterns for listings
    # Try multiple selectors that Carousell might use
    listing_containers = []
    
    # Pattern 1: Modern Carousell card structure
    listing_containers.extend(soup.select('[data-testid*="listing"]'))
    
    # Pattern 2: Class-based cards
    listing_containers.extend(soup.select('div[class*="card"], div[class*="listing"], div[class*="product"]'))
    
    # Pattern 3: Link-based listings (common in search results)
    listing_containers.extend(soup.select('a[href*="/p/"], a[href*="/listing/"]'))
    
    # Pattern 4: Generic article/item patterns
    listing_containers.extend(soup.select('article, [role="listitem"]'))
    
    # Deduplicate by removing nested elements
    seen_texts = set()
    unique_containers = []
    
    for container in listing_containers:
        text_content = container.get_text(strip=True)[:100]  # First 100 chars for dedup
        if text_content and text_content not in seen_texts:
            seen_texts.add(text_content)
            unique_containers.append(container)
    
    print(f"DOM_PARSER: Found {len(unique_containers)} potential listing containers")
    
    for idx, container in enumerate(unique_containers[:20]):  # Limit to first 20
        listing = extract_listing_info(container, idx)
        if listing and listing.get("price", 0) > 0:
            listings.append(listing)
    
    print(f"DOM_PARSER: ✓ Extracted {len(listings)} valid listings")
    return listings


def extract_listing_info(container, index: int) -> Optional[dict]:
    """
    Extract listing information from a container element.
    
    Args:
        container: BeautifulSoup element containing listing
        index: Index number for this listing
        
    Returns:
        Dictionary with listing info or None
    """
    try:
        # Extract title - try various patterns
        title_elem = (
            container.select_one('[data-testid*="title"], h2, h3, [class*="title"]') or
            container.select_one('p, span')
        )
        title = title_elem.get_text(strip=True) if title_elem else ""
        
        # Extract price - look for currency patterns
        price_text = ""
        # Try specific attribute first
        price_elem = container.select_one('[data-testid*="price"], [class*="price"]')
        if price_elem:
            price_text = price_elem.get_text(strip=True)
        
        # If still empty or no number found, try regex on full container text
        if not price_text or not re.search(r'\d', price_text):
            full_text = container.get_text(" ", strip=True)
            # Regex to find: S$123, $123, 123.45 (with or without From)
            price_match = re.search(r'(?:S?\$|From\s+S?\$)\s*([\d,]+(?:\.\d{2})?)', full_text, re.IGNORECASE)
            if price_match:
                price_text = price_match.group(0)
            else:
                # Last resort: just find any number with a $ nearby
                price_match = re.search(r'[\d,]+(?:\.\d{2})?', full_text)
                if price_match:
                    price_text = price_match.group(0)
        
        price = parse_price(price_text)
        
        # Extract seller info
        seller_elem = container.select_one('[class*="seller"], [class*="user"], [class*="owner"]')
        seller_name = seller_elem.get_text(strip=True) if seller_elem else "Unknown Seller"
        
        # Extract URLs
        link_elem = container.select_one('a[href]') or container if container.name == 'a' else None
        listing_url = ""
        if link_elem and link_elem.get('href'):
            href = link_elem.get('href', '')
            listing_url = f"https://www.carousell.sg{href}" if href.startswith('/') else href
        
        # Extract image
        img_elem = container.select_one('img[src]')
        image_url = img_elem.get('src', '') if img_elem else ""
        
        # Generate CSS selector for chat button
        # Carousell chat buttons are usually on listing detail pages
        chat_selector = f'[data-testid="chat-button"], button:has-text("Chat"), a:has-text("Chat")'
        
        # Skip if no meaningful title or price
        if not title or len(title) < 3:
            return None
            
        return {
            "index": index,
            "title": title[:100],  # Truncate long titles
            "price": price,
            "price_raw": price_text,
            "seller_name": seller_name,
            "seller_url": "",
            "listing_url": listing_url,
            "chat_selector": chat_selector,
            "image_url": image_url,
            "condition": "",
            "location": "",
        }
        
    except Exception as e:
        print(f"DOM_PARSER: Warning - Failed to parse container {index}: {e}")
        return None


def filter_listings_by_price(listings: list[dict], max_price: float) -> list[dict]:
    """
    Filter listings to only those under a maximum price.
    
    Args:
        listings: List of listing dictionaries
        max_price: Maximum price threshold
        
    Returns:
        Filtered list of listings
    """
    filtered = [l for l in listings if 0 < l.get("price", 0) <= max_price]
    print(f"DOM_PARSER: Filtered to {len(filtered)} listings under ${max_price}")
    return filtered


def format_listings_for_display(listings: list[dict]) -> str:
    """
    Format listings as a readable string for CLI display.
    
    Args:
        listings: List of listing dictionaries
        
    Returns:
        Formatted string representation
    """
    if not listings:
        return "No listings found."
    
    lines = ["=" * 60, f"Found {len(listings)} listings:", "=" * 60]
    
    for listing in listings:
        lines.append(
            f"[{listing['index']}] {listing['title']}\n"
            f"    💰 {listing['price_raw']} | 👤 {listing['seller_name']}\n"
            f"    🔗 {listing['listing_url'][:60]}..."
        )
        lines.append("-" * 60)
    
    return "\n".join(lines)


# Standalone test with mock Carousell-like HTML
if __name__ == "__main__":
    print("=" * 50)
    print("DOM PARSER TEST (Mock Carousell HTML)")
    print("=" * 50)
    
    # Mock Carousell search results HTML
    mock_html = """
    <!DOCTYPE html>
    <html>
    <head><title>iPhone - Carousell</title></head>
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
    </body>
    </html>
    """
    
    dom_data = {"html": mock_html, "url": "https://carousell.sg/search/iphone"}
    
    listings = parse_listings(dom_data)
    
    print(f"\n✓ Extracted {len(listings)} listings:")
    for l in listings:
        print(f"  [{l['index']}] {l['title']} - ${l['price']}")
    
    # Test filtering
    filtered = filter_listings_by_price(listings, 3000)
    print(f"\n✓ Listings under $3000: {len(filtered)}")
    
    # Test display formatting
    print("\n" + format_listings_for_display(listings))
    
    print("\nDOM_PARSER: ✓ All tests passed!")
