function ChatHistory({ messages, finalPrice }) {
  const formatTime = (timestamp) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('en-SG', { hour: '2-digit', minute: '2-digit' })
  }

  return (
    <div className="chat-history">
      {finalPrice && (
        <div className="deal-banner">
          Deal closed at <strong>${finalPrice}</strong>
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
  )
}

function getRoundPercent(round) {
  const percents = { 1: '65%', 2: '85%', 3: '95%', 4: '100%', 5: 'walk' }
  return percents[round] || ''
}

export default ChatHistory
