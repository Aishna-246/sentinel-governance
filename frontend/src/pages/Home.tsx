import type { CSSProperties } from 'react'
import { useEffect, useState } from 'react'

type Dimension = {
  name: string
  score: number
  max_score: number
  passed: boolean
  reason: string
}

type ScoreResponse = {
  governance_score?: {
    total_score?: number
    grade?: string
    dimensions?: Dimension[]
  }
}

type ModelResponse = Array<Record<string, unknown>>

const pageStyle: CSSProperties = {
  backgroundColor: '#F9FAFB',
  padding: '32px',
  minHeight: '100vh',
}

const cardStyle: CSSProperties = {
  backgroundColor: 'white',
  borderRadius: '16px',
  boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
  padding: '32px',
  marginBottom: '24px',
}

const rowStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '48px',
}

const bottomRowStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '1fr 1fr',
  gap: '24px',
}

const labelStyle: CSSProperties = {
  fontSize: '11px',
  letterSpacing: '3px',
  color: '#9CA3AF',
  textTransform: 'uppercase',
  marginBottom: '8px',
}

const scoreNumberStyle: CSSProperties = {
  fontSize: '80px',
  fontWeight: 800,
  color: '#1A3C5E',
  lineHeight: 1,
}

const detailLabelStyle: CSSProperties = {
  fontSize: '14px',
  color: '#6B7280',
}

const detailValueStyle: CSSProperties = {
  fontSize: '14px',
  fontWeight: 600,
  color: '#1A3C5E',
}

function formatDimensionName(name: string) {
  return name
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

function getGradeBadgeStyle(grade: string): CSSProperties {
  const base: CSSProperties = {
    fontSize: '28px',
    fontWeight: 700,
    padding: '4px 16px',
    borderRadius: '999px',
    marginLeft: '16px',
    alignSelf: 'center',
  }

  switch (grade) {
    case 'A':
      return { ...base, backgroundColor: '#D1FAE5', color: '#065F46' }
    case 'B':
      return { ...base, backgroundColor: '#DBEAFE', color: '#1E40AF' }
    case 'C':
      return { ...base, backgroundColor: '#FEF3C7', color: '#92400E' }
    case 'D':
      return { ...base, backgroundColor: '#FFEDD5', color: '#9A3412' }
    default:
      return { ...base, backgroundColor: '#FEE2E2', color: '#991B1B' }
  }
}

function Home() {
  const [scoreData, setScoreData] = useState<ScoreResponse | null>(null)
  const [models, setModels] = useState<ModelResponse>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()

    async function loadData() {
      try {
        setLoading(true)
        setError(null)

        const [scoreRes, modelsRes] = await Promise.all([
          fetch('http://localhost:8000/api/score', { signal: controller.signal }),
          fetch('http://localhost:8000/api/models', { signal: controller.signal }),
        ])

        if (!scoreRes.ok || !modelsRes.ok) {
          throw new Error('Unable to load dashboard data')
        }

        const scoreJson = await scoreRes.json()
        const modelsJson = await modelsRes.json()

        setScoreData(scoreJson)
        setModels(Array.isArray(modelsJson) ? modelsJson : [])
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

    loadData()

    return () => controller.abort()
  }, [])

  if (loading) {
    return (
      <div style={{ ...pageStyle, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontSize: '18px', color: '#374151' }}>Loading...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div style={pageStyle}>
        <div
          style={{
            backgroundColor: '#FEE2E2',
            border: '1px solid #FECACA',
            color: '#991B1B',
            borderRadius: '16px',
            padding: '24px',
          }}
        >
          {error}
        </div>
      </div>
    )
  }

  const dimensions = scoreData?.governance_score?.dimensions ?? []
  const totalScore = scoreData?.governance_score?.total_score ?? 0
  const grade = scoreData?.governance_score?.grade ?? 'F'
  const humanReviewDimension = dimensions.find((item) => item.name === 'human_review_rate')
  const unreviewedDecisions = humanReviewDimension ? Math.max(0, 20 - humanReviewDimension.score) : 0

  return (
    <div style={pageStyle}>
      <div style={cardStyle}>
        <div style={rowStyle}>
          <div>
            <div style={labelStyle}>GOVERNANCE SCORE</div>
            <div style={{ display: 'flex', alignItems: 'flex-end' }}>
              <div style={scoreNumberStyle}>{totalScore}</div>
              <div style={getGradeBadgeStyle(grade)}>{grade}</div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '12px', flex: 1 }}>
            {dimensions.map((dimension) => {
              const passedStyle: React.CSSProperties = {
                border: dimension.passed ? '1.5px solid #BBF7D0' : '1.5px solid #FECACA',
                borderRadius: '12px',
                padding: '12px',
                flex: 1,
                backgroundColor: dimension.passed ? '#F0FDF4' : '#FFF5F5',
              }
              const iconStyle: React.CSSProperties = {
                color: dimension.passed ? '#16A34A' : '#DC2626',
                fontWeight: 'bold',
                marginRight: '4px',
              }
              return (
                <div key={dimension.name} style={passedStyle}>
                  <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                    <span style={iconStyle}>{dimension.passed ? '✓' : '✗'}</span>
                    <span
                      style={{
                        fontSize: '10px',
                        fontWeight: 600,
                        color: '#6B7280',
                        textTransform: 'uppercase',
                      }}
                    >
                      {formatDimensionName(dimension.name)}
                    </span>
                  </div>
                  <div style={{ fontSize: '22px', fontWeight: 700, color: '#1A3C5E', margin: '4px 0' }}>
                    {dimension.score}/{dimension.max_score}
                  </div>
                  <div
                    style={{
                      fontSize: '11px',
                      color: '#6B7280',
                      lineHeight: 1.4,
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden',
                    }}
                  >
                    {dimension.reason}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      <div style={bottomRowStyle}>
        <div style={cardStyle}>
          <div style={{ fontSize: '16px', fontWeight: 600, color: '#1A3C5E', marginBottom: '16px' }}>
            Policy Frameworks
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid #F3F4F6' }}>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <span style={{ color: '#16A34A', marginRight: '8px' }}>●</span>
              <span style={{ fontSize: '14px', color: '#111827' }}>DPDP Act 2023 / Rules 2025</span>
            </div>
            <span style={{ backgroundColor: '#D1FAE5', color: '#065F46', fontSize: '11px', padding: '2px 10px', borderRadius: '999px', fontWeight: 600 }}>
              Active
            </span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid #F3F4F6' }}>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <span style={{ color: '#2563EB', marginRight: '8px' }}>●</span>
              <span style={{ fontSize: '14px', color: '#111827' }}>GDPR (EU) 2016/679</span>
            </div>
            <span style={{ backgroundColor: '#DBEAFE', color: '#1E40AF', fontSize: '11px', padding: '2px 10px', borderRadius: '999px', fontWeight: 600 }}>
              Stub
            </span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0' }}>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <span style={{ color: '#9CA3AF', marginRight: '8px' }}>●</span>
              <span style={{ fontSize: '14px', color: '#111827' }}>EU AI Act 2024</span>
            </div>
            <span style={{ backgroundColor: '#F3F4F6', color: '#6B7280', fontSize: '11px', padding: '2px 10px', borderRadius: '999px', fontWeight: 600 }}>
              Planned
            </span>
          </div>
        </div>

        <div style={cardStyle}>
          <div style={{ fontSize: '16px', fontWeight: 600, color: '#1A3C5E', marginBottom: '16px' }}>
            Platform Overview
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid #F3F4F6' }}>
            <span style={detailLabelStyle}>Total Models</span>
            <span style={detailValueStyle}>{models.length}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid #F3F4F6' }}>
            <span style={detailLabelStyle}>Active Framework</span>
            <span style={detailValueStyle}>DPDP Act 2023</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid #F3F4F6' }}>
            <span style={detailLabelStyle}>Unreviewed Decisions</span>
            <span style={{ ...detailValueStyle, color: unreviewedDecisions > 0 ? '#D97706' : '#16A34A' }}>
              {unreviewedDecisions}
            </span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0' }}>
            <span style={detailLabelStyle}>Version</span>
            <span style={detailValueStyle}>v1.0.0</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Home
