import { useState, useEffect, useRef } from 'react'
import ProductRow from './components/ProductRow/ProductRow'
import { mockData } from './data/mockData'
import { fetchLiveData, mergeLiveWithMock } from './utils/liveDataLoader'
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
  const [isRecording, setIsRecording] = useState(false)
  const chatEndRef = useRef(null)

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

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

  const handleMic = async () => {
    if (isRecording || isSending) return

    setIsRecording(true)

    // Add visual feedback
    setMessages(prev => [...prev, {
      timestamp: new Date().toLocaleTimeString(),
      sender: 'SYSTEM',
      text: '🎤 Recording... Speak into your microphone'
    }])

    try {
      await fetch('http://127.0.0.1:5001/cmd', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: 'voice' })
      })
    } catch (err) {
      console.error('Failed to send voice command:', err)
      setMessages(prev => [...prev, {
        timestamp: new Date().toLocaleTimeString(),
        sender: 'ERROR',
        text: 'Failed to start voice recording. Is the agent running?'
      }])
    } finally {
      // Recording takes ~10 seconds on backend
      setTimeout(() => setIsRecording(false), 12000)
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
          disabled={isSending || isRecording}
        />
        <button
          type="button"
          className={`mic-btn ${isRecording ? 'recording' : ''}`}
          onClick={handleMic}
          disabled={isSending || isRecording}
          title="Record voice message"
        >
          {isRecording ? '🔴' : '🎤'}
        </button>
        <button type="submit" disabled={isSending || isRecording}>
          {isSending ? '...' : 'Send'}
        </button>
      </form>
    </div>
  )
}

function App() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [liveData, setLiveData] = useState(null)

  // Poll for live negotiation data
  useEffect(() => {
    const loadLiveData = async () => {
      const data = await fetchLiveData()
      if (data) {
        setLiveData(data)
      }
    }

    loadLiveData()
    const interval = setInterval(loadLiveData, 2000)
    return () => clearInterval(interval)
  }, [])

  // Merge live data with mock data - live data appears first
  const allData = mergeLiveWithMock(liveData, mockData)

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
            {Object.entries(allData).map(([productName, data]) => (
              <ProductRow key={productName} productName={productName} data={data} />
            ))}
          </div>
        </div>
      </main>
    </div>
  )
}

export default App
