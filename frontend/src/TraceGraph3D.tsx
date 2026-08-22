import { useEffect, useRef } from 'react'
// @ts-ignore -- 3d-force-graph doesn't ship polished TypeScript types.
import ForceGraph3D from '3d-force-graph'

const Graph3D = ForceGraph3D as any

type FileResult = {
  path: string
  owner: string | null
  blast_radius_count: number
  blast_radius_files: string[]
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
  file: '#EDEDF0',
  blast: '#5F5E5A',
}

// Blast radius lists can be large (50+ for a central file) -- capping
// keeps the graph readable. The real count is still shown as text
// separately, so nothing is hidden, just not all drawn as nodes.
const MAX_BLAST_NODES_PER_FILE = 12

function buildGraphData(result: Candidate, query: string) {
  const nodes: any[] = [{ id: 'query', label: query, group: 'query', val: 4 }]
  const links: any[] = []
  const seen = new Set(['query'])

  const candidateId = `${result.type}:${result.id}`
  nodes.push({ id: candidateId, label: result.preview, group: result.type, val: 4 })
  seen.add(candidateId)
  links.push({ source: 'query', target: candidateId })

  result.files.forEach((f) => {
    if (!seen.has(f.path)) {
      nodes.push({ id: f.path, label: f.path, group: 'file', val: 3 })
      seen.add(f.path)
    }
    links.push({ source: candidateId, target: f.path })

    f.blast_radius_files.slice(0, MAX_BLAST_NODES_PER_FILE).forEach((bf) => {
      if (!seen.has(bf)) {
        nodes.push({ id: bf, label: bf, group: 'blast', val: 1 })
        seen.add(bf)
      }
      links.push({ source: f.path, target: bf })
    })
  })

  return { nodes, links }
}

function TraceGraph3D({
  result,
  query,
  expanded,
}: {
  result: Candidate
  query: string
  expanded: boolean
}) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!containerRef.current) return

    const data = buildGraphData(result, query)
    const height = expanded ? 560 : 320

    const graph = Graph3D()(containerRef.current)
      .graphData(data)
      .nodeLabel('label')
      .nodeColor((n: any) => COLORS[n.group] || '#888780')
      .nodeVal('val')
      .nodeRelSize(4)
      .linkColor(() => 'rgba(160,158,200,0.55)')
      .linkWidth(0.6)
      .backgroundColor('#16161B')
      .width(containerRef.current.clientWidth)
      .height(height)

    setTimeout(() => {
      graph.zoomToFit(400, 40)
    }, 500)

    return () => {
      if (containerRef.current) containerRef.current.innerHTML = ''
    }
  }, [result, query, expanded])

  const anyCapped = result.files.some((f) => f.blast_radius_files.length > MAX_BLAST_NODES_PER_FILE)

  return (
    <div>
      <div className="graph-legend">
        <span><span className="dot" style={{ background: COLORS.query }} /> query</span>
        <span><span className="dot" style={{ background: COLORS.pull_request }} /> pull request</span>
        <span><span className="dot" style={{ background: COLORS.commit }} /> commit</span>
        <span><span className="dot" style={{ background: COLORS.file }} /> touched file</span>
        <span><span className="dot" style={{ background: COLORS.blast }} /> affected file</span>
      </div>
      {anyCapped && (
        <p className="graph-note">Showing up to {MAX_BLAST_NODES_PER_FILE} affected files per file — see the list above for the full count.</p>
      )}
      <div ref={containerRef} className="trace-graph" />
    </div>
  )
}

export default TraceGraph3D