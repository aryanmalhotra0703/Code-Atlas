import { useEffect, useRef, useState } from 'react'
// @ts-ignore -- no polished TypeScript types shipped for this library
import ForceGraph2D from 'react-force-graph-2d'

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

const COLORS = ['#7F77DD', '#378ADD', '#1D9E75', '#D85A30', '#BA7517', '#9891E8']

function ArchitectureView() {
  const [data, setData] = useState<ArchitectureResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const graphRef = useRef<any>(null)

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

  const maxFiles = Math.max(...data.modules.map((m) => m.file_count))

  const graphData = {
    nodes: data.modules.map((m, i) => ({
      id: m.module,
      val: m.file_count,
      color: COLORS[i % COLORS.length],
    })),
    links: data.edges.map((e) => ({
      source: e.from_module,
      target: e.to_module,
      weight: e.weight,
    })),
  }

  return (
    <div>
      <h2 className="hero-title" style={{ fontSize: '1.4rem', textAlign: 'left' }}>
        Architecture
      </h2>
      <p className="subtitle" style={{ textAlign: 'left', marginBottom: '1.5rem' }}>
        Auto-generated from the real import graph — node size reflects file count,
        line thickness reflects import weight between modules.
      </p>

      <div ref={containerRef} className="architecture-graph">
        <ForceGraph2D
          ref={graphRef}
          graphData={graphData}
          nodeLabel={(n: any) => `${n.id} — ${n.val} files`}
          nodeRelSize={6}
          nodeColor={(n: any) => n.color}
          linkWidth={(l: any) => Math.max(l.weight / 8, 1.5)}
          linkColor={() => 'rgba(160,158,200,0.7)'}
          linkDirectionalParticles={2}
          linkDirectionalParticleWidth={2}
          backgroundColor="#0B0B0E"
          width={containerRef.current?.clientWidth || 700}
          height={420}
          onEngineStop={() => graphRef.current?.zoomToFit(400, 60)}
        />
      </div>

      <div className="module-grid">
        {data.modules.map((m) => (
          <div key={m.module} className="module-card">
            <code>{m.module}</code>
            <div className="module-bar">
              <div
                className="module-bar-fill"
                style={{ width: `${(m.file_count / maxFiles) * 100}%` }}
              />
            </div>
            <span className="similarity">{m.file_count} files</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default ArchitectureView