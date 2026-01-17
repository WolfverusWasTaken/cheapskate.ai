import { useState, useEffect } from 'react'
import ItemCard from './components/ItemCard'
import { mockData } from './data/mockData'
import './App.css'

function LiveStream() {
  const [currentUrl, setCurrentUrl] = useState(null)
  const [nextUrl, setNextUrl] = useState(`/live.jpg?t=${Date.now()}`)
  const [hasStarted, setHasStarted] = useState(false)

  useEffect(() => {
    const interval = setInterval(() => {
      const timestamp = Date.now()
      setNextUrl(`/live.jpg?t=${timestamp}`)
    }, 500)
    return () => clearInterval(interval)
  }, [])

  const handleNextLoaded = () => {
    setCurrentUrl(nextUrl)
    setHasStarted(true)
  }

  return (
    <div className="live-stream">
      {hasStarted ? (
        <img
          src={currentUrl}
          className="live-frame"
          alt="Live Browser Stream"
        />
      ) : (
        <div className="stream-placeholder">
          <div className="pulse-slow"></div>
          <p>Waiting for Agent...</p>
        </div>
      )}

      {/* Background Buffer */}
      <img
        src={nextUrl}
        style={{ display: 'none' }}
        onLoad={handleNextLoaded}
        onError={() => {
          // Keep trying, agent might not be running yet
        }}
      />

    </div>
  )
}

function ChatPanel() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isSending, setIsSending] = useState(false)
  const chatEndRef = useState(null)

  // Poll for logs
  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const response = await fetch('/logs.json?t=' + Date.now())
        if (response.ok) {
          const logs = await response.json()
          setMessages(logs)
        }
      } catch (e) {
        // Silently ignore log fetch errors if agent isn't running
      }
    }

    const interval = setInterval(fetchLogs, 1000)
    return () => clearInterval(interval)
  }, [])

  const handleSend = async (e) => {
    e.preventDefault()
    if (!input.trim() || isSending) return

    setIsSending(true)
    const command = input.trim()

    try {
      await fetch('http://127.0.0.1:5001/cmd', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command })
      })
      setInput('')
    } catch (err) {
      console.error('Failed to send command:', err)
      // Add local error message
      setMessages(prev => [...prev, {
        timestamp: new Date().toLocaleTimeString(),
        sender: 'ERROR',
        text: 'Failed to connect to agent bridge (127.0.0.1:5001). Is the agent running?'
      }])
    } finally {
      setIsSending(false)
    }
  }

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <h3>Agent CLI</h3>
        <span className="status-dot"></span>
      </div>
      <div className="chat-log">
        {messages.length === 0 && (
          <div className="no-logs">Waiting for agent activity...</div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`log-entry ${msg.sender.toLowerCase()}`}>
            <span className="log-time">{msg.timestamp}</span>
            <span className="log-sender">[{msg.sender}]</span>
            <span className="log-text">{msg.text}</span>
          </div>
        ))}
        <div ref={chatEndRef} />
      </div>
      <form className="chat-input" onSubmit={handleSend}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a command (e.g., find mice)..."
          disabled={isSending}
        />
        <button type="submit" disabled={isSending}>
          {isSending ? '...' : 'Send'}
        </button>
      </form>
    </div>
  )
}

function App() {
  const [activeTab, setActiveTab] = useState('dashboard')

  return (
    <div className="app">
      <header className="header">
        <h1>Lowballer</h1>
        <nav className="tabs">
          <button
            className={`tab ${activeTab === 'browser' ? 'active' : ''}`}
            onClick={() => setActiveTab('browser')}
          >
            Browser
          </button>
          <button
            className={`tab ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            Dashboard
          </button>
        </nav>
      </header>

      <main className="main">
        <div className={`tab-content ${activeTab === 'browser' ? 'active' : 'hidden'}`}>
          <div className="layout-split">
            <div className="browser-container">
              <LiveStream />
            </div>
            <ChatPanel />
          </div>
        </div>

        <div className={`tab-content ${activeTab === 'dashboard' ? 'active' : 'hidden'}`}>
          <div className="item-list">
            {Object.entries(mockData).map(([itemName, data]) => (
              <ItemCard key={itemName} itemName={itemName} data={data} />
            ))}
          </div>
        </div>
      </main>
    </div>
  )
}

export default App
