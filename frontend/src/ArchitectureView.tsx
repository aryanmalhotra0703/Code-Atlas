import { useEffect, useState } from 'react'

type ModuleInfo = {
  module: string
  file_count: number
}

type ModuleEdge = {
  from_module: string
  to_module: string
  weight: number
}

type ArchitectureResponse = {
  modules: ModuleInfo[]
  edges: ModuleEdge[]
}

function ArchitectureView() {
  const [data, setData] = useState<ArchitectureResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('http://localhost:8000/api/architecture')
      .then((res) => {
        if (!res.ok) throw new Error(`Request failed: ${res.status}`)
        return res.json()
      })
      .then(setData)
      .catch(() => setError('Could not reach the backend. Is the API running?'))
  }, [])

  if (error) return <p className="error">{error}</p>
  if (!data) return <p className="subtitle">Loading…</p>

  return (
    <div>
      <p className="subtitle">
        Auto-generated from the real import graph — modules grouped by
        top-level folder.
      </p>

      <div className="module-grid">
        {data.modules.map((m) => (
          <div key={m.module} className="module-card">
            <code>{m.module}</code>
            <span className="similarity">{m.file_count} files</span>
          </div>
        ))}
      </div>

      <h3>Dependencies between modules</h3>
      <ul className="files">
        {data.edges.map((e) => (
          <li key={`${e.from_module}-${e.to_module}`}>
            <code>{e.from_module}</code> → <code>{e.to_module}</code>
            <span className="similarity"> ({e.weight} import{e.weight === 1 ? '' : 's'})</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default ArchitectureView