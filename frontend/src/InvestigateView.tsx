import TraceGraph3D from './TraceGraph3D'
import { useState } from 'react'

type FileResult = {
  path: string
  owner: string | null
  blast_radius_count: number
}

type Candidate = {
  type: string
  id: string
  similarity: number
  preview: string
  files: FileResult[]
}

type InvestigateResponse = {
  query: string
  repo: string
  results: Candidate[]
}

function InvestigateView() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Candidate[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showGraph, setShowGraph] = useState(false)

  async function runInvestigation(e: React.FormEvent) {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    setError(null)

    try {
      const res = await fetch(
        `http://localhost:8000/api/investigate?query=${encodeURIComponent(query)}`
      )
      if (!res.ok) throw new Error(`Request failed: ${res.status}`)
      const data: InvestigateResponse = await res.json()
      setResults(data.results)
    } catch (err) {
      setError('Could not reach the backend. Is the API running?')
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <p className="subtitle">Describe a problem, trace it to real code.</p>

      <form onSubmit={runInvestigation} className="query-form">
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

      {error && <p className="error">{error}</p>}

      <div className="results">
        {results.map((r) => (
          <div key={`${r.type}-${r.id}`} className="result-card">
            <div className="result-header">
              <span className="badge">{r.type}</span>
              <span>{r.id}</span>
              <span className="similarity">similarity: {r.similarity}</span>
            </div>
            <p className="preview">{r.preview}</p>
            {r.files.length > 0 && (
              <ul className="files">
                {r.files.map((f) => (
                  <li key={f.path}>
                    <code>{f.path}</code>
                    {f.owner && <span> — owner: {f.owner}</span>}
                    <span> — blast radius: {f.blast_radius_count} files</span>
                  </li>
                ))}
              </ul>
            )}
            {results.length > 0 && (
            <button className="graph-toggle" onClick={() => setShowGraph(!showGraph)}>
                {showGraph ? 'Hide 3D trace' : 'View 3D trace'}
            </button>
            )}
            {showGraph && results.length > 0 && <TraceGraph3D results={results} query={query} />}
          </div>
        ))}
      </div>
    </div>
  )
}

export default InvestigateView