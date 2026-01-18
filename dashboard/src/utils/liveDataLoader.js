/**
 * Load and transform live negotiation data from chat_history.json
 * The agent writes data keyed by seller_id, we need to group by product
 */

export async function fetchLiveData() {
  try {
    const response = await fetch('/chat_history.json?t=' + Date.now())
    if (!response.ok) {
      return null
    }
    const rawData = await response.json()
    return transformToProductFormat(rawData)
  } catch (e) {
    console.log('No live data available:', e.message)
    return null
  }
}

/**
 * Transform flat seller_id keyed data into product-grouped format
 * Input: { "seller_product": { listing, messages, ... }, ... }
 * Output: { "Product Name": { listings: [], negotiations: {} }, ... }
 */
function transformToProductFormat(rawData) {
  const products = {}

  for (const [sellerId, negotiation] of Object.entries(rawData)) {
    const productName = negotiation.listing?.title
    if (!productName) continue

    // Initialize product entry if needed
    if (!products[productName]) {
      products[productName] = {
        listings: [],
        negotiations: {}
      }
    }

    // Add to negotiations
    products[productName].negotiations[sellerId] = negotiation

    // Add to listings if not already there
    const sellerName = negotiation.listing?.seller_name
    const price = negotiation.listing?.price
    if (sellerName && price) {
      const existingListing = products[productName].listings.find(
        l => l.seller === sellerName
      )
      if (!existingListing) {
        products[productName].listings.push({
          seller: sellerName,
          price: price
        })
      }
    }
  }

  return products
}

/**
 * Merge live data with mock data, prioritizing live data
 */
export function mergeLiveWithMock(liveData, mockData) {
  if (!liveData) {
    return mockData
  }

  const merged = { ...liveData }

  // Add mock data entries that aren't in live data
  for (const [productName, data] of Object.entries(mockData)) {
    if (!merged[productName]) {
      merged[productName] = data
    }
  }

  return merged
}
