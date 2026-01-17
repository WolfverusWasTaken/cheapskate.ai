import { useState } from 'react'

function NegotiationCard({ negotiation }) {
  const [showChat, setShowChat] = useState(false)

  const { listing, messages, current_round, status, final_price } = negotiation

  const formatTime = (timestamp) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('en-SG', { hour: '2-digit', minute: '2-digit' })
  }

  const lastOffer = [...messages].reverse().find(m => m.offer_price)?.offer_price

  return (
    <div className={`negotiation-card ${status}`}>
      <div className="neg-header" onClick={() => setShowChat(!showChat)}>
        <div className="neg-info">
          <span className="neg-seller">@{listing.seller_name}</span>
          <span className="neg-price">${listing.price}</span>
          <span className="neg-round">Round {current_round}/5</span>
          <span className={`neg-status ${status}`}>
            {status === 'walked_away' ? 'walked' : status}
          </span>
        </div>
        <div className="neg-actions">
          {lastOffer && <span className="last-offer">Last: ${lastOffer}</span>}
          <span className={`chat-toggle ${showChat ? 'open' : ''}`}>
            {showChat ? '▲ Hide' : '▼ Chat'}
          </span>
        </div>
      </div>

      {showChat && (
        <div className="chat-history">
          {final_price && (
            <div className="deal-banner">
              Deal closed at <strong>${final_price}</strong>
            </div>
          )}

          {messages.map((msg, idx) => (
            <div key={idx} className={`chat-msg ${msg.role}`}>
              <div className="msg-header">
                <span className="msg-role">{msg.role === 'lowballer' ? 'You' : 'Seller'}</span>
                {msg.round && (
                  <span className={`msg-round round-${msg.round}`}>
                    R{msg.round} ({getRoundPercent(msg.round)})
                  </span>
                )}
                <span className="msg-time">{formatTime(msg.timestamp)}</span>
              </div>
              <p className="msg-text">{msg.content}</p>
              {msg.offer_price && (
                <span className="msg-offer">→ ${msg.offer_price}</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function getRoundPercent(round) {
  const percents = { 1: '65%', 2: '85%', 3: '95%', 4: '100%', 5: 'walk' }
  return percents[round] || ''
}

export default NegotiationCard
