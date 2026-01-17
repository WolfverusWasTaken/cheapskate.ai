import { useState } from 'react'
import ItemCard from './components/ItemCard'
import { mockData } from './data/mockData'
import './App.css'

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
        {activeTab === 'browser' ? (
          <div className="browser-placeholder">
            <div className="placeholder-icon">🖥</div>
            <p>Playwright browser will be embedded here</p>
            <span className="placeholder-hint">Live automation view</span>
          </div>
        ) : (
          <div className="item-list">
            {Object.entries(mockData).map(([itemName, data]) => (
              <ItemCard key={itemName} itemName={itemName} data={data} />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

export default App
