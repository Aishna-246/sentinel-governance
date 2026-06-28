import type { CSSProperties } from 'react'
import { useEffect, useState } from 'react'

type ModelCard = {
  model_name: string
  version: string
  stage: string
  dpdp_risk: string
  pii_columns: string[]
  external_api: string
}

const pageStyle: CSSProperties = {
  backgroundColor: '#F9FAFB',
  padding: '32px',
  minHeight: '100vh',
}

const cardStyle: CSSProperties = {
  backgroundColor: 'white',
  borderRadius: '16px',
  boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
  overflow: 'hidden',
}

const tableStyle: CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse',
}

const headerRowStyle: CSSProperties = {
  backgroundColor: '#1A3C5E',
}

const headerCellStyle: CSSProperties = {
  color: 'white',
  fontSize: '12px',
  fontWeight: 600,
  textTransform: 'uppercase',
  letterSpacing: '1px',
  padding: '14px 20px',
  textAlign: 'left',
}

const cellStyle: CSSProperties = {
  padding: '14px 20px',
  fontSize: '14px',
  color: '#374151',
  borderBottom: '1px solid #F3F4F6',
}

const nameCellStyle: CSSProperties = {
  fontWeight: 600,
  color: '#1A3C5E',
}

const subtitleStyle: CSSProperties = {
  fontSize: '14px',
  color: '#6B7280',
  marginBottom: '24px',
}

const badgeBaseStyle: CSSProperties = {
  fontSize: '12px',
  padding: '2px 10px',
  borderRadius: '999px',
  fontWeight: 600,
}

const errorStyle: CSSProperties = {
  backgroundColor: '#FEE2E2',
  border: '1px solid #FECACA',
  color: '#991B1B',
  borderRadius: '16px',
  padding: '20px',
  marginBottom: '24px',
}

function getStageBadgeStyle(stage: string): CSSProperties {
  const lower = stage.toLowerCase()
  if (lower === 'production') {
    return { ...badgeBaseStyle, backgroundColor: '#D1FAE5', color: '#065F46' }
  }
  if (lower === 'staging') {
    return { ...badgeBaseStyle, backgroundColor: '#FEF3C7', color: '#92400E' }
  }
  return { ...badgeBaseStyle, backgroundColor: '#F3F4F6', color: '#6B7280' }
}

function getRiskBadgeStyle(risk: string): CSSProperties {
  const lower = risk.toLowerCase()
  if (lower === 'high') {
    return { ...badgeBaseStyle, backgroundColor: '#FEE2E2', color: '#991B1B' }
  }
  if (lower === 'medium') {
    return { ...badgeBaseStyle, backgroundColor: '#FEF3C7', color: '#92400E' }
  }
  return { ...badgeBaseStyle, backgroundColor: '#D1FAE5', color: '#065F46' }
}

export default function Models() {
  const [models, setModels] = useState<ModelCard[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()

    async function fetchModels() {
      try {
        setLoading(true)
        setError(null)

        const response = await fetch('http://localhost:8000/api/models', { signal: controller.signal })
        if (!response.ok) {
          throw new Error('Unable to load models')
        }

        const data = await response.json()
        setModels(Array.isArray(data) ? data : [])
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

    fetchModels()

    return () => controller.abort()
  }, [])

  return (
    <div style={pageStyle}>
      <div style={{ marginBottom: '8px', fontSize: '24px', fontWeight: 700, color: '#1A3C5E' }}>
        Model Inventory
      </div>
      <div style={subtitleStyle}>All registered models from MLflow registry</div>

      {loading ? (
        <div style={{ fontSize: '16px', color: '#374151' }}>Loading...</div>
      ) : error ? (
        <div style={errorStyle}>{error}</div>
      ) : (
        <div style={cardStyle}>
          <table style={tableStyle}>
            <thead style={headerRowStyle}>
              <tr>
                <th style={headerCellStyle}>Model Name</th>
                <th style={headerCellStyle}>Version</th>
                <th style={headerCellStyle}>Stage</th>
                <th style={headerCellStyle}>DPDP Risk</th>
                <th style={headerCellStyle}>PII Columns</th>
                <th style={headerCellStyle}>External API</th>
              </tr>
            </thead>
            <tbody>
              {models.map((model, index) => {
                const rowBackground = index % 2 === 0 ? '#F9FAFB' : 'white'
                const piiText = model.pii_columns && model.pii_columns.length > 0 ? model.pii_columns.join(', ') : 'None'
                return (
                  <tr key={`${model.model_name}-${model.version}`} style={{ backgroundColor: rowBackground }}>
                    <td style={{ ...cellStyle, ...nameCellStyle }}>{model.model_name}</td>
                    <td style={cellStyle}>{model.version}</td>
                    <td style={cellStyle}>
                      <span style={getStageBadgeStyle(model.stage)}>{model.stage}</span>
                    </td>
                    <td style={cellStyle}>
                      <span style={getRiskBadgeStyle(model.dpdp_risk)}>{model.dpdp_risk}</span>
                    </td>
                    <td style={{ ...cellStyle, fontSize: '12px', color: '#6B7280', fontStyle: model.pii_columns?.length ? 'normal' : 'italic' }}>
                      {piiText}
                    </td>
                    <td style={cellStyle}>
                      {model.external_api ? (
                        <span style={{ ...badgeBaseStyle, backgroundColor: '#DBEAFE', color: '#1E40AF' }}>{model.external_api}</span>
                      ) : (
                        '—'
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
