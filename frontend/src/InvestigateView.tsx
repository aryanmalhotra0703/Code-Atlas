import { useState } from 'react'
import TraceGraph3D from './TraceGraph3D'

type FileResult = {
  path: string
  owner: string | null
  blast_radius_count: number
  blast_radius_files: string[]
}

type ScoreBreakdown = {
  total: number
  similarity_component: number
  recency_component: number
  blast_component: number
}

type Candidate = {
  type: string
  id: string
  similarity: number
  preview: string
  files: FileResult[]
  composite_score?: number
  score_breakdown?: ScoreBreakdown
}

type InvestigateResponse = {
  query: string
  repo: string
  results: Candidate[]
  message?: string
}

type RepoStats = {
  full_name: string
  primary_language: string | null
  file_count: number
  last_synced_at: string | null
}

const EXAMPLE_QUERIES = [
  'SSL certificate verification is failing',
  'JSON output formatting is broken',
  'redirect handling is incorrect',
]

function shorten(text: string, wordLimit: number = 6): string {
  const words = text.split(' ')
  if (words.length <= wordLimit) return text
  return words.slice(0, wordLimit).join(' ') + '…'
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

// Raw cosine similarity scores (e.g. 0.58 vs 0.57) aren't meaningfully
// interpretable as "58% correct" -- what actually matters is how each
// result ranks *relative to the others in this set*. Scaling against
// this result set's own min/max turns a cluster of near-identical raw
// numbers into an honest, readable relevance signal.
function relativeRelevance(score: number, all: Candidate[]): number {
  const scores = all.map((r) => r.similarity)
  const min = Math.min(...scores)
  const max = Math.max(...scores)
  if (max === min) return 100
  return Math.round(((score - min) / (max - min)) * 100)
}

// Deterministic color per owner name -- same person always gets the same
// avatar color across the whole app, without needing a lookup table.
function ownerColor(name: string): string {
  const colors = ['#7F77DD', '#378ADD', '#1D9E75', '#D85A30', '#BA7517']
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash)
  return colors[Math.abs(hash) % colors.length]
}

function ScoreBar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const pct = Math.min((value / max) * 100, 100)
  return (
    <div className="score-bar-row">
      <span className="score-bar-label">{label}</span>
      <div className="score-bar-track">
        <div className="score-bar-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="score-bar-value">{value.toFixed(3)}</span>
    </div>
  )
}

function InvestigateView({ stats }: { stats: RepoStats | null }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Candidate[]>([])
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)
  const [showGraph, setShowGraph] = useState(false)
  const [graphExpanded, setGraphExpanded] = useState(false)
  const [loading, setLoading] = useState(false)
  const [loadingStatus, setLoadingStatus] = useState('Embedding query…')
  const [error, setError] = useState<string | null>(null)
  const [history, setHistory] = useState<string[]>([])

  async function runQuery(q: string) {
    if (!q.trim()) return

    setLoading(true)
    setError(null)

    // These labels are cosmetic -- the real request is one network call,
    // not three literal stages. Cycling text just gives a sense of
    // progress while genuinely waiting on the backend.
    const statuses = ['Embedding query…', 'Searching for matches…', 'Traversing the graph…']
    let statusIndex = 0
    setLoadingStatus(statuses[0])
    const statusInterval = setInterval(() => {
      statusIndex = (statusIndex + 1) % statuses.length
      setLoadingStatus(statuses[statusIndex])
    }, 900)

    try {
      const res = await fetch(
        `http://localhost:8000/api/investigate?query=${encodeURIComponent(q)}`
      )
      const data: InvestigateResponse = await res.json()
      if (!res.ok) {
        throw new Error((data as any).detail || `Request failed: ${res.status}`)
      }
      setResults(data.results)
      if (data.message) {
        setError(data.message)
      }
      setSelectedIndex(data.results.length > 0 ? 0 : null)
      setShowGraph(false)
      setGraphExpanded(false)
      setHistory((prev) => [q, ...prev.filter((h) => h !== q)].slice(0, 6))
    } catch (err) {
      setError('Could not reach the backend. Is the API running?')
      setResults([])
      setSelectedIndex(null)
    } finally {
      clearInterval(statusInterval)
      setLoading(false)
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    runQuery(query)
  }

  const selected = selectedIndex !== null ? results[selectedIndex] : null

  return (
    <div>
      <div className="hero">
        {stats && (
          <div className="live-badge">
            <span className="live-dot" />
            Live · {stats.full_name} · Last synced {timeAgo(stats.last_synced_at)}
          </div>
        )}
        <h2 className="hero-title">Investigate your codebase</h2>
        <p className="subtitle">Describe a problem, trace it to real code.</p>
      </div>

      <form onSubmit={handleSubmit} className="query-form">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. SSL certificate verification is failing"
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Investigating…' : 'Investigate'}
        </button>
      </form>

      {results.length === 0 && !loading && (
        <div className="example-chips">
          <span className="example-label">Try:</span>
          {EXAMPLE_QUERIES.map((eq) => (
            <button
              key={eq}
              className="example-chip"
              onClick={() => {
                setQuery(eq)
                runQuery(eq)
              }}
            >
              {eq}
            </button>
          ))}
        </div>
      )}

      {history.length > 0 && (
        <div className="history-pills">
          {history.map((h) => (
            <button key={h} className="history-pill" onClick={() => { setQuery(h); runQuery(h) }}>
              {shorten(h, 5)}
            </button>
          ))}
        </div>
      )}

      {error && <p className="error">{error}</p>}

      {loading && (
        <div className="skeleton-wrap">
          <p className="skeleton-status">{loadingStatus}</p>
          <div className="split-layout">
            <div className="result-list">
              {[1, 2, 3].map((i) => (
                <div key={i} className="skeleton-row" />
              ))}
            </div>
            <div className="detail-panel skeleton-panel" />
          </div>
        </div>
      )}

      {!loading && results.length > 0 && (
        <div className="split-layout">
          <div className="result-list">
            {results.map((r, i) => {
              const rel = relativeRelevance(r.similarity, results)
              return (
                <div
                  key={`${r.type}-${r.id}`}
                  className={i === selectedIndex ? 'result-row active' : 'result-row'}
                  onClick={() => {
                    setSelectedIndex(i)
                    setShowGraph(false)
                    setGraphExpanded(false)
                  }}
                >
                  <div className="result-row-top">
                    <span className={`badge badge-${r.type}`}>{r.type}</span>
                  </div>
                  <p className="result-row-title">{shorten(r.preview)}</p>
                  <div className="relevance-bar" title={`raw score: ${r.similarity}`}>
                    <div className="relevance-fill" style={{ width: `${rel}%` }} />
                  </div>
                </div>
              )
            })}
          </div>

          <div className="detail-panel">
            {selected && (
              <>
                <div className="result-header">
                  <span className={`badge badge-${selected.type}`}>{selected.type}</span>
                  <span>{selected.id}</span>
                </div>
                <p className="preview" title={selected.preview}>{selected.preview}</p>

                {selected.score_breakdown && (
                  <div className="score-breakdown">
                    <ScoreBar label="Semantic" value={selected.score_breakdown.similarity_component} max={0.5} color="#7F77DD" />
                    <ScoreBar label="Recency" value={selected.score_breakdown.recency_component} max={0.3} color="#378ADD" />
                    <ScoreBar label="Blast radius" value={selected.score_breakdown.blast_component} max={0.2} color="#D85A30" />
                  </div>
                )}

                {selected.files.length > 0 && (
                  <div className="file-cards">
                    {selected.files.map((f) => (
                      <div key={f.path} className="file-card">
                        <div className="file-card-top">
                          <code className="file-path">{f.path}</code>
                          {f.blast_radius_count > 30 && <span className="hot-badge">🔥 HOT</span>}
                        </div>
                        {f.owner && (
                          <div className="owner-row">
                            <span
                              className="owner-avatar"
                              style={{ background: ownerColor(f.owner) }}
                            >
                              {f.owner.charAt(0).toUpperCase()}
                            </span>
                            <span className="owner-name">{f.owner}</span>
                          </div>
                        )}
                        <div className="blast-bar-row">
                          <div className="blast-bar">
                            <div
                              className="blast-bar-fill"
                              style={{ width: `${Math.min((f.blast_radius_count / 60) * 100, 100)}%` }}
                            />
                          </div>
                          <span className="blast-count">{f.blast_radius_count} files</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {selected.files.length > 0 && (
                  <div className="graph-controls">
                    <button className="graph-toggle" onClick={() => setShowGraph(!showGraph)}>
                      {showGraph ? 'Hide graph' : 'Show blast radius graph'}
                    </button>
                    {showGraph && (
                      <button className="graph-toggle" onClick={() => setGraphExpanded(!graphExpanded)}>
                        {graphExpanded ? 'Shrink' : 'Enlarge'}
                      </button>
                    )}
                  </div>
                )}

                {showGraph && (
                  <TraceGraph3D result={selected} query={query} expanded={graphExpanded} />
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default InvestigateView