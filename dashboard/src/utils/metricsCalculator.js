/**
 * Calculate deal metrics for a product
 * @param {Object} negotiations - All negotiations for a product
 * @returns {{totalSavings: number, averageDiscount: number, bestDeal: number}}
 */
export function calculateDealMetrics(negotiations) {
  const acceptedDeals = Object.values(negotiations || {})
    .filter(neg => neg.status === 'accepted' && neg.final_price)

  if (acceptedDeals.length === 0) {
    return { totalSavings: 0, averageDiscount: 0, bestDeal: 0 }
  }

  // Total Savings = sum of (listing_price - final_price)
  const totalSavings = acceptedDeals.reduce((sum, neg) => {
    return sum + (neg.listing.price - neg.final_price)
  }, 0)

  // Average Discount % = average of ((listing_price - final_price) / listing_price * 100)
  const discounts = acceptedDeals.map(neg => {
    return ((neg.listing.price - neg.final_price) / neg.listing.price) * 100
  })
  const averageDiscount = discounts.reduce((a, b) => a + b, 0) / discounts.length

  // Best Deal = highest discount percentage
  const bestDeal = Math.max(...discounts)

  return {
    totalSavings: Math.round(totalSavings),
    averageDiscount: Math.round(averageDiscount * 10) / 10,
    bestDeal: Math.round(bestDeal * 10) / 10
  }
}

/**
 * Get the lowest price achieved in negotiations
 * @param {Object} negotiation - Single negotiation object
 * @returns {number|null}
 */
export function getLowestPriceSoFar(negotiation) {
  if (!negotiation) return null

  if (negotiation.final_price) {
    return negotiation.final_price
  }

  const offers = negotiation.messages
    .filter(m => m.offer_price)
    .map(m => m.offer_price)

  return offers.length > 0 ? Math.min(...offers) : negotiation.listing.price
}

/**
 * Get chat preview snippet
 * @param {Array} messages - Message array
 * @param {number} maxLength - Max characters
 * @returns {string}
 */
export function getChatPreview(messages, maxLength = 50) {
  if (!messages || messages.length === 0) {
    return 'No messages yet'
  }

  const lastMessage = messages[messages.length - 1]
  const content = lastMessage.content

  if (content.length <= maxLength) {
    return content
  }

  return content.substring(0, maxLength) + '...'
}
