import { useState } from 'react'
import './App.css'
import InvestigateView from './InvestigateView'
import ArchitectureView from './ArchitectureView'

function App() {
  const [tab, setTab] = useState<'investigate' | 'architecture'>('investigate')

  return (
    <div className="app">
      <h1>Code Atlas</h1>

      <div className="tabs">
        <button
          className={tab === 'investigate' ? 'tab active' : 'tab'}
          onClick={() => setTab('investigate')}
        >
          Investigate
        </button>
        <button
          className={tab === 'architecture' ? 'tab active' : 'tab'}
          onClick={() => setTab('architecture')}
        >
          Architecture
        </button>
      </div>

      {tab === 'investigate' ? <InvestigateView /> : <ArchitectureView />}
    </div>
  )
}

export default App