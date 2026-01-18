import SellerCard from '../SellerCard'

function SellerChatPanel({ negotiations, listings }) {
  const negotiationEntries = Object.entries(negotiations || {})

  // Get sellers who have negotiations
  const negotiatedSellers = new Set(
    negotiationEntries.map(([, neg]) => neg.listing.seller_name)
  )

  // Sellers without negotiations
  const otherListings = listings.filter(l => !negotiatedSellers.has(l.seller))

  const hasContent = negotiationEntries.length > 0 || otherListings.length > 0

  return (
    <div className="seller-chat-panel">
      <div className="seller-chat-panel__header">Seller Negotiations</div>

      <div className="seller-chat-panel__list">
        {!hasContent && (
          <div className="seller-chat-panel__empty">No negotiations yet</div>
        )}

        {/* Sellers with active negotiations first */}
        {negotiationEntries
          .sort(([, a], [, b]) => {
            // Sort: active first, then accepted, then walked_away
            const order = { active: 0, accepted: 1, walked_away: 2 }
            return (order[a.status] || 3) - (order[b.status] || 3)
          })
          .map(([id, negotiation]) => (
            <SellerCard key={id} negotiation={negotiation} />
          ))
        }

        {/* Other sellers without negotiations */}
        {otherListings.map((listing, idx) => (
          <SellerCard key={`listing-${idx}`} listing={listing} />
        ))}
      </div>
    </div>
  )
}

export default SellerChatPanel
