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

function InvestigateView({ stats }: { stats: RepoStats | null }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Candidate[]>([])
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)
  const [showGraph, setShowGraph] = useState(false)
  const [graphExpanded, setGraphExpanded] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [history, setHistory] = useState<string[]>([])

  async function runQuery(q: string) {
    if (!q.trim()) return

    setLoading(true)
    setError(null)

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

      {results.length > 0 && (
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

                {selected.files.length > 0 && (
                  <ul className="files">
                    {selected.files.map((f) => (
                      <li key={f.path}>
                        <code>{f.path}</code>
                        {f.owner && <span> — owner: {f.owner}</span>}
                        <span> — blast radius: {f.blast_radius_count} files</span>
                      </li>
                    ))}
                  </ul>
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