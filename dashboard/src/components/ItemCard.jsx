import { useState } from 'react'
import NegotiationCard from './NegotiationCard'

function ItemCard({ itemName, data }) {
  const [expanded, setExpanded] = useState(false)

  const { listings, negotiations } = data
  const prices = listings.map(l => l.price)
  const lowest = Math.min(...prices)
  const highest = Math.max(...prices)
  const average = Math.round(prices.reduce((a, b) => a + b, 0) / prices.length)

  const negotiationEntries = Object.entries(negotiations || {})
  const activeCount = negotiationEntries.filter(([, n]) => n.status === 'active').length

  // Listings without active negotiations
  const negotiatedSellers = new Set(negotiationEntries.map(([, n]) => n.listing.seller_name))
  const otherListings = listings.filter(l => !negotiatedSellers.has(l.seller))

  return (
    <div className={`item-card ${expanded ? 'expanded' : ''}`}>
      <div className="item-card-header" onClick={() => setExpanded(!expanded)}>
        <div className="item-info">
          <span className="item-name">{itemName}</span>
          <span className="item-meta">
            {listings.length} listings
            {activeCount > 0 && <span className="active-badge">{activeCount} active</span>}
          </span>
        </div>

        <div className="price-stats">
          <div className="price-stat">
            <span className="price-value low">${lowest}</span>
            <span className="price-label">lowest</span>
          </div>
          <div className="price-stat">
            <span className="price-value avg">${average}</span>
            <span className="price-label">avg</span>
          </div>
          <div className="price-stat">
            <span className="price-value high">${highest}</span>
            <span className="price-label">highest</span>
          </div>
        </div>

        <span className={`chevron ${expanded ? 'open' : ''}`}>▼</span>
      </div>

      {expanded && (
        <div className="item-card-content">
          {negotiationEntries.length > 0 && (
            <div className="section">
              <h3 className="section-title">Negotiations</h3>
              <div className="negotiation-list">
                {negotiationEntries.map(([id, neg]) => (
                  <NegotiationCard key={id} negotiation={neg} />
                ))}
              </div>
            </div>
          )}

          {otherListings.length > 0 && (
            <div className="section">
              <h3 className="section-title">Other Listings</h3>
              <div className="other-listings">
                {otherListings.map((listing, idx) => (
                  <div key={idx} className="listing-chip">
                    <span className="listing-seller">@{listing.seller}</span>
                    <span className="listing-price">${listing.price}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default ItemCard
