import { useEffect, useRef } from 'react'
// @ts-ignore -- 3d-force-graph doesn't ship polished TypeScript types;
// using `any` internally here rather than fighting incomplete type defs
// for a visualization layer that sits outside the core engine.
import ForceGraph3D from '3d-force-graph'

const Graph3D = ForceGraph3D as any

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

const COLORS: Record<string, string> = {
  query: '#D85A30',
  commit: '#1D9E75',
  pull_request: '#378ADD',
  file: '#888780',
}

function buildGraphData(results: Candidate[], query: string) {
  const nodes: any[] = [{ id: 'query', label: query, group: 'query' }]
  const links: any[] = []

  results.forEach((r) => {
    const candidateId = `${r.type}:${r.id}`
    nodes.push({ id: candidateId, label: r.preview, group: r.type })
    links.push({ source: 'query', target: candidateId })

    r.files.forEach((f) => {
      if (!nodes.find((n) => n.id === f.path)) {
        nodes.push({ id: f.path, label: f.path, group: 'file' })
      }
      links.push({ source: candidateId, target: f.path })
    })
  })

  return { nodes, links }
}

function TraceGraph3D({ results, query }: { results: Candidate[]; query: string }) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!containerRef.current) return

    const data = buildGraphData(results, query)

    const graph = Graph3D()(containerRef.current)
      .graphData(data)
      .nodeLabel('label')
      .nodeColor((n: any) => COLORS[n.group] || '#888780')
      .nodeRelSize(4)
      .linkColor(() => 'rgba(150,150,150,0.4)')
      .backgroundColor('#ffffff')
      .width(containerRef.current.clientWidth)
      .height(300)

    // The force-directed layout needs a moment to settle before the
    // camera can frame it correctly -- zoomToFit right away would
    // frame the *starting* positions, not the settled ones. A short
    // delay lets the physics simulation stabilize first.
    setTimeout(() => {
      graph.zoomToFit(400, 40)
    }, 500)

    // 3d-force-graph has no formal teardown API -- clearing the
    // container on unmount/re-render is the pragmatic cleanup.
    return () => {
      if (containerRef.current) containerRef.current.innerHTML = ''
    }
  }, [results, query])

  return (
    <div>
      <div className="graph-legend">
        <span><span className="dot" style={{ background: COLORS.query }} /> query</span>
        <span><span className="dot" style={{ background: COLORS.pull_request }} /> pull request</span>
        <span><span className="dot" style={{ background: COLORS.commit }} /> commit</span>
        <span><span className="dot" style={{ background: COLORS.file }} /> file</span>
      </div>
      <div ref={containerRef} className="trace-graph" />
    </div>
  )
}

export default TraceGraph3D