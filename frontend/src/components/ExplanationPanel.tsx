import { useState, useEffect } from 'react'
import { getExplanation } from '../services/api'

interface Props {
  sessionId: string
  selectedText: string
  surroundingText: string
  page: number
  onClose: () => void
}

type Mode = 'quick' | 'deep' | 'prerequisites' | 'why_it_matters'

const MODE_LABELS: Record<Mode, string> = {
  quick: 'Quick explanation',
  deep: 'Deeper explanation',
  prerequisites: 'What should I know first?',
  why_it_matters: 'Why does this matter?',
}

export default function ExplanationPanel({
  sessionId, selectedText, surroundingText, page, onClose,
}: Props) {
  const [mode, setMode] = useState<Mode>('quick')
  const [content, setContent] = useState<string | null>(null)
  const [relatedConcepts, setRelatedConcepts] = useState<string[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchExplanation('quick')
  }, [selectedText])

  async function fetchExplanation(m: Mode) {
    setMode(m)
    setLoading(true)
    try {
      const data = await getExplanation(sessionId, selectedText, surroundingText, page, m)
      setContent(data.content)
      setRelatedConcepts(data.related_concepts || [])
    } catch {
      setContent('Unable to generate explanation.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="explanation-panel">
      <div className="panel-header">
        <span className="panel-title">Context</span>
        <button className="panel-close" onClick={onClose}>&times;</button>
      </div>

      <div className="panel-selection">
        <p className="selection-label">Selected text</p>
        <blockquote className="selection-text">"{selectedText}"</blockquote>
      </div>

      <div className="panel-modes">
        {(Object.keys(MODE_LABELS) as Mode[]).map(m => (
          <button
            key={m}
            className={`mode-btn ${mode === m ? 'active' : ''}`}
            onClick={() => fetchExplanation(m)}
          >
            {MODE_LABELS[m]}
          </button>
        ))}
      </div>

      <div className="panel-content">
        {loading ? (
          <div className="panel-loading">
            <div className="spinner small" />
          </div>
        ) : (
          <>
            <p>{content}</p>
            {relatedConcepts.length > 0 && (
              <div className="related-concepts">
                <span className="related-label">Related: </span>
                {relatedConcepts.map((c, i) => (
                  <span key={i} className="concept-tag">{c}</span>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
