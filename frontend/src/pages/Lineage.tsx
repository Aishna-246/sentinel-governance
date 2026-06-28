import type { CSSProperties } from 'react'
import { useEffect, useState } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useEdgesState,
  useNodesState,
} from 'reactflow'
import 'reactflow/dist/style.css'

const pageStyle: CSSProperties = {
  backgroundColor: '#F9FAFB',
  padding: '32px',
  minHeight: '100vh',
  display: 'flex',
  flexDirection: 'column',
}

const titleStyle: CSSProperties = {
  fontSize: '24px',
  fontWeight: 700,
  color: '#1A3C5E',
  marginBottom: '8px',
}

const subtitleStyle: CSSProperties = {
  fontSize: '14px',
  color: '#6B7280',
  marginBottom: '24px',
}

const legendRowStyle: CSSProperties = {
  display: 'flex',
  gap: '24px',
  flexWrap: 'wrap',
  marginBottom: '16px',
}

const legendItemStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '6px',
  fontSize: '12px',
  color: '#6B7280',
}

const legendDotStyle = (color: string): CSSProperties => ({
  display: 'inline-block',
  width: '10px',
  height: '10px',
  borderRadius: '50%',
  backgroundColor: color,
})

const flowContainerStyle: CSSProperties = {
  width: '100%',
  height: '600px',
  backgroundColor: 'white',
  borderRadius: '16px',
  boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
  border: '1px solid #E5E7EB',
}

const errorStyle: CSSProperties = {
  backgroundColor: '#FEE2E2',
  border: '1px solid #FECACA',
  color: '#991B1B',
  borderRadius: '16px',
  padding: '20px',
  marginBottom: '24px',
}

const nodeStyles: Record<string, CSSProperties> = {
  dataset: {
    background: '#EFF6FF',
    border: '2px solid #3B82F6',
    borderRadius: '10px',
    padding: '10px 16px',
    fontSize: '12px',
    fontWeight: 600,
    color: '#1E40AF',
    minWidth: '120px',
    textAlign: 'center',
  },
  model: {
    background: '#1A3C5E',
    border: '2px solid #1A3C5E',
    borderRadius: '10px',
    padding: '10px 16px',
    fontSize: '12px',
    fontWeight: 600,
    color: 'white',
    minWidth: '140px',
    textAlign: 'center',
  },
  api: {
    background: '#F3F4F6',
    border: '2px solid #9CA3AF',
    borderRadius: '10px',
    padding: '10px 16px',
    fontSize: '12px',
    fontWeight: 600,
    color: '#374151',
    minWidth: '120px',
    textAlign: 'center',
  },
  llm_vendor: {
    background: '#FEF2F2',
    border: '2px solid #EF4444',
    borderRadius: '10px',
    padding: '10px 16px',
    fontSize: '12px',
    fontWeight: 600,
    color: '#991B1B',
    minWidth: '100px',
    textAlign: 'center',
  },
  decision: {
    background: '#FFFBEB',
    border: '2px solid #F59E0B',
    borderRadius: '10px',
    padding: '10px 16px',
    fontSize: '12px',
    fontWeight: 600,
    color: '#92400E',
    minWidth: '120px',
    textAlign: 'center',
  },
  audit: {
    background: '#ECFDF5',
    border: '2px solid #10B981',
    borderRadius: '10px',
    padding: '10px 16px',
    fontSize: '12px',
    fontWeight: 600,
    color: '#065F46',
    minWidth: '100px',
    textAlign: 'center',
  },
}

export default function Lineage() {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()

    async function fetchGraph() {
      try {
        setLoading(true)
        setError(null)

        const response = await fetch('http://localhost:8000/api/lineage/graph', { signal: controller.signal })
        if (!response.ok) {
          throw new Error('Unable to load lineage graph')
        }

        const data = await response.json()

        const styledNodes = data.nodes.map((node: any) => ({
          ...node,
          originalType: node.type,
          type: 'default',
          position: {
            x: Number(node.position?.x || 0),
            y: Number(node.position?.y || 0),
          },
          style: nodeStyles[node.type] || nodeStyles.api,
          data: {
            ...node.data,
            originalType: node.type,
            label: node.data?.label || node.id,
          },
        }))

        const styledEdges = data.edges.map((edge: any) => ({
          ...edge,
          style: edge.data?.pii_flow
            ? { stroke: '#EF4444', strokeWidth: 2, strokeDasharray: '5,5' }
            : { stroke: '#9CA3AF', strokeWidth: 1.5 },
          animated: edge.data?.pii_flow ? true : false,
        }))

        setNodes(styledNodes)
        setEdges(styledEdges)
      } catch (fetchError) {
        if (fetchError instanceof Error && fetchError.name !== 'AbortError') {
          setError(fetchError.message)
        } else if (!(fetchError instanceof Error)) {
          setError('Unknown error occurred')
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    fetchGraph()

    return () => controller.abort()
  }, [])

  return (
    <div style={pageStyle}>
      <div style={titleStyle}>Model Lineage Graph</div>
      <div style={subtitleStyle}>Dataset → Model → API → Decision → Audit flow</div>
      <div style={legendRowStyle}>
        <div style={legendItemStyle}>
          <span style={legendDotStyle('#3B82F6')} />
          Dataset
        </div>
        <div style={legendItemStyle}>
          <span style={legendDotStyle('#1A3C5E')} />
          Model
        </div>
        <div style={legendItemStyle}>
          <span style={legendDotStyle('#6B7280')} />
          API Endpoint
        </div>
        <div style={legendItemStyle}>
          <span style={legendDotStyle('#EF4444')} />
          LLM Vendor
        </div>
        <div style={legendItemStyle}>
          <span style={legendDotStyle('#10B981')} />
          Audit Log
        </div>
        <div style={legendItemStyle}>
          <span style={{ color: '#EF4444' }}>─ ─</span>
          PII Flow
        </div>
      </div>

      {loading ? (
        <div style={{ fontSize: '16px', color: '#374151' }}>Loading...</div>
      ) : error ? (
        <div style={errorStyle}>{error}</div>
      ) : (
        <div style={flowContainerStyle}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            fitView
            fitViewOptions={{ padding: 0.3 }}
            defaultEdgeOptions={{ type: 'smoothstep' }}
          >
            <Background color="#E5E7EB" gap={20} />
            <Controls />
            <MiniMap
              nodeColor={(node) => {
                const colors: Record<string, string> = {
                  dataset: '#3B82F6',
                  model: '#1A3C5E',
                  api: '#9CA3AF',
                  llm_vendor: '#EF4444',
                  decision: '#F59E0B',
                  audit: '#10B981',
                }
                return colors[(node.data as any)?.originalType as string] || '#9CA3AF'
              }}
              style={{ backgroundColor: '#F9FAFB' }}
            />
          </ReactFlow>
        </div>
      )}
    </div>
  )
}
