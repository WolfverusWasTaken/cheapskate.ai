import { useState } from 'react'
import ChatHistory from './ChatHistory'
import { getLowestPriceSoFar, getChatPreview } from '../utils/metricsCalculator'

function SellerCard({ negotiation, listing }) {
  const [expanded, setExpanded] = useState(false)

  // Use negotiation data if available, otherwise use listing
  const sellerName = negotiation?.listing.seller_name || listing?.seller
  const listingPrice = negotiation?.listing.price || listing?.price
  const status = negotiation?.status || 'pending'
  const messages = negotiation?.messages || []
  const finalPrice = negotiation?.final_price

  const lowestPrice = negotiation ? getLowestPriceSoFar(negotiation) : listingPrice
  const preview = getChatPreview(messages)

  return (
    <div className={`seller-card seller-card--${status}`}>
      <div className="seller-card__header" onClick={() => setExpanded(!expanded)}>
        <div className="seller-card__info">
          <span className="seller-card__handle">@{sellerName}</span>
          <span className="seller-card__price">
            ${lowestPrice}
            {lowestPrice !== listingPrice && (
              <span className="seller-card__original"> (was ${listingPrice})</span>
            )}
          </span>
          <span className="seller-card__preview">{preview}</span>
        </div>

        <div className="seller-card__actions">
          <span className={`seller-card__status seller-card__status--${status}`}>
            {status === 'walked_away' ? 'walked' : status}
          </span>
          <span className="seller-card__expand">
            {expanded ? '▲ Hide' : '▼ Chat'}
          </span>
        </div>
      </div>

      {expanded && messages.length > 0 && (
        <div className="seller-card__content">
          <ChatHistory messages={messages} finalPrice={finalPrice} />
        </div>
      )}

      {expanded && messages.length === 0 && (
        <div className="seller-card__content">
          <p className="seller-card__empty">No chat history yet</p>
        </div>
      )}
    </div>
  )
}

export default SellerCard
