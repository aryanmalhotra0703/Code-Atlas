import { useEffect, useState } from 'react'
import './App.css'
import InvestigateView from './InvestigateView'
import ArchitectureView from './ArchitectureView'

type RepoStats = {
  full_name: string
  primary_language: string | null
  file_count: number
  last_synced_at: string | null
}

function timeAgo(isoString: string | null): string {
  if (!isoString) return 'never synced'
  const diffMs = Date.now() - new Date(isoString).getTime()
  const mins = Math.floor(diffMs / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

function App() {
  const [tab, setTab] = useState<'investigate' | 'architecture'>('investigate')
  const [stats, setStats] = useState<RepoStats | null>(null)

  useEffect(() => {
    fetch('http://localhost:8000/api/stats')
      .then((res) => res.json())
      .then(setStats)
      .catch(() => setStats(null))
  }, [])

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="logo-badge">CA</div>
          <span className="logo-text">Code Atlas</span>
        </div>

        <div className="sidebar-section">
          <p className="sidebar-label">Repository</p>
          <div className="repo-card">
            <span className="repo-dot" />
            <div>
              <p className="repo-name">{stats ? stats.full_name : 'Loading…'}</p>
              <p className="repo-meta">
                {stats
                  ? `${stats.file_count} files · ${stats.primary_language ?? 'Unknown'}`
                  : ''}
              </p>
              {stats && (
                <p className="repo-meta">Synced {timeAgo(stats.last_synced_at)}</p>
              )}
            </div>
          </div>
        </div>

        <div className="sidebar-section">
          <p className="sidebar-label">Views</p>
          <button
            className={tab === 'investigate' ? 'nav-item active' : 'nav-item'}
            onClick={() => setTab('investigate')}
          >
            Investigate
          </button>
          <button
            className={tab === 'architecture' ? 'nav-item active' : 'nav-item'}
            onClick={() => setTab('architecture')}
          >
            Architecture
          </button>
        </div>
      </aside>

      <main className="content">
        {tab === 'investigate' ? <InvestigateView /> : <ArchitectureView />}
      </main>
    </div>
  )
}

export default App