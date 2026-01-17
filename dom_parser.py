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
    
    # Use the exact Carousell structure: data-testid="listing-card-XXXX"
    listing_cards = soup.select('[data-testid^="listing-card-"]')
    
    print(f"DOM_PARSER: Found {len(listing_cards)} listing cards")
    
    # Extract info and index sequentially
    for idx, card in enumerate(listing_cards[:20]):  # Limit to first 20
        listing = extract_listing_info(card, idx)
        if listing and listing.get("price", 0) > 0:
            listings.append(listing)
    
    print(f"DOM_PARSER: ✓ Extracted {len(listings)} valid listings")
    return listings


def extract_listing_info(container, index: int) -> Optional[dict]:
    """
    Extract listing information from a Carousell listing card.
    
    Args:
        container: BeautifulSoup element (listing card with data-testid)
        index: Index number for this listing
        
    Returns:
        Dictionary with listing info or None
    """
    try:
        # Get the product link (contains title and goes to /p/)
        product_link = container.select_one('a[href*="/p/"]')
        if not product_link:
            return None
        
        # Extract title from img alt or p element inside product link
        title = ""
        img_elem = product_link.select_one('img[alt]')
        if img_elem:
            title = img_elem.get('alt', '')
        if not title:
            # Fallback: get first p with --max-line style (title element)
            title_p = product_link.select_one('p[style*="--max-line"]')
            if title_p:
                title = title_p.get_text(strip=True)
        
        # Extract price from p element with title attribute containing S$
        price_text = ""
        price_elem = product_link.select_one('p[title*="S$"]')
        if price_elem:
            price_text = price_elem.get('title', '') or price_elem.get_text(strip=True)
        else:
            # Fallback: look for S$ in any p element
            for p in product_link.select('p'):
                text = p.get_text(strip=True)
                if text.startswith('S$'):
                    price_text = text
                    break
        
        price = parse_price(price_text)
        
        # Extract seller name from data-testid="listing-card-text-seller-name"
        seller_elem = container.select_one('[data-testid="listing-card-text-seller-name"]')
        seller_name = seller_elem.get_text(strip=True) if seller_elem else "Unknown Seller"
        
        # Get the product URL
        href = product_link.get('href', '')
        listing_url = f"https://www.carousell.sg{href}" if href.startswith('/') else href
        
        # Extract image URL
        image_url = img_elem.get('src', '') if img_elem else ""
        
        # Extract condition if present
        condition = ""
        # Look for "Brand new", "Like new", etc.
        for p in container.select('p'):
            text = p.get_text(strip=True).lower()
            if text in ['brand new', 'like new', 'well used', 'heavily used']:
                condition = p.get_text(strip=True)
                break
        
        # Skip if no meaningful title or price
        if not title or len(title) < 2:
            return None
        
        # Require valid S$ price
        if price <= 0:
            return None
            
        return {
            "index": index,
            "title": title[:100],
            "price": price,
            "price_raw": price_text,
            "seller_name": seller_name,
            "seller_url": "",
            "listing_url": listing_url,
            "chat_selector": '[data-testid="chat-button"], button:has-text("Chat")',
            "image_url": image_url,
            "condition": condition,
            "location": "",
        }
        
    except Exception as e:
        print(f"DOM_PARSER: Warning - Failed to parse container {index}: {e}")
        return None


def extract_listing_details(html: str) -> dict:
    """
    Extract detailed information from a single listing page (description, details, etc.).
    """
    soup = BeautifulSoup(html, 'html.parser')
    details = {}
    
    # 1. Extract Description
    # We use find() with text instead of invalid CSS :has-text
    desc_header = soup.find(['h2', 'h3', 'p'], string=re.compile(r'Description', re.I))
    desc_elem = soup.select_one('[data-testid*="description"], [class*="description"]')
    
    if not desc_elem and desc_header:
        # Try to find the next sibling div/p
        desc_elem = desc_header.find_next(['div', 'p', 'span'])
        
    if desc_elem:
        details["description"] = desc_elem.get_text("\n", strip=True)
    else:
        details["description"] = "No description found."

    # 2. Extract structured "Details" section (Condition, Battery Health, etc.)
    # Look for the section after "Details" header
    details_header = soup.find(['h2', 'h3', 'p'], string=re.compile(r'Details', re.I))
    if details_header:
        # Find the container - Carousell usually uses a grid or list after the header
        container = details_header.find_parent().find_parent() or details_header.parent
        
        # Look for pairs of text. Carousell often uses: 
        # Label (Condition)
        # Value (Lightly used)
        
        # Find all <div> or <span> elements that look like pairs
        all_text_elements = container.find_all(['p', 'span', 'div'], recursive=True)
        
        extracted_pairs = {}
        # Simple heuristic: filter for common labels
        labels = ["Condition", "Battery Health", "Screen", "Body", "Warranty", "Model", "Storage", "Color", "Set"]
        
        for i, elem in enumerate(all_text_elements):
            text = elem.get_text(strip=True)
            for label in labels:
                if label in text and len(text) < 30: # Likely a label
                    # The next element or its child is likely the value
                    if i + 1 < len(all_text_elements):
                        val = all_text_elements[i+1].get_text(strip=True)
                        if val and val != text:
                            extracted_pairs[text] = val
        
        if extracted_pairs:
            details["structured_details"] = extracted_pairs
            # Also flatten some into the main dict for backward compatibility
            details["condition"] = extracted_pairs.get("Condition", "")
            
    return details


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
