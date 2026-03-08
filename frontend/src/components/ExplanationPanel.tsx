import { useState, useEffect } from 'react'
import { getExplanation, webResearch } from '../services/api'

interface Props {
  sessionId: string
  selectedText: string
  surroundingText: string
  page: number
  onClose: () => void
}

type Mode = 'quick' | 'deep' | 'prerequisites' | 'why_it_matters'

interface WebSource {
  title: string
  url: string
  snippet: string
  source: string
}

interface ResearchResult {
  title: string
  url: string
  snippet: string
  source: string
}

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
  const [webSources, setWebSources] = useState<WebSource[]>([])
  const [loading, setLoading] = useState(false)
  const [researchResults, setResearchResults] = useState<ResearchResult[]>([])
  const [researchLoading, setResearchLoading] = useState(false)
  const [showResearch, setShowResearch] = useState(false)

  useEffect(() => {
    fetchExplanation('quick')
    setResearchResults([])
    setShowResearch(false)
  }, [selectedText])

  async function fetchExplanation(m: Mode) {
    setMode(m)
    setLoading(true)
    try {
      const data = await getExplanation(sessionId, selectedText, surroundingText, page, m)
      setContent(data.content)
      setRelatedConcepts(data.related_concepts || [])
      setWebSources(data.web_sources || [])
    } catch {
      setContent('Unable to generate explanation. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  async function fetchResearch() {
    setResearchLoading(true)
    setShowResearch(true)
    try {
      const data = await webResearch(sessionId, selectedText, page)
      setResearchResults(data.results || [])
    } catch {
      setResearchResults([])
    } finally {
      setResearchLoading(false)
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
        <button
          className={`mode-btn research-btn ${showResearch ? 'active' : ''}`}
          onClick={fetchResearch}
        >
          Search the Web
        </button>
      </div>

      <div className="panel-content">
        {loading ? (
          <div className="panel-loading">
            <div className="spinner small" />
            <p className="loading-text">Generating explanation...</p>
          </div>
        ) : (
          <>
            <div className="explanation-text">
              {content?.split('\n').map((line, i) => (
                line.trim() ? <p key={i}>{line}</p> : null
              ))}
            </div>
            {relatedConcepts.length > 0 && (
              <div className="related-concepts">
                <span className="related-label">Related: </span>
                {relatedConcepts.map((c, i) => (
                  <span key={i} className="concept-tag">{c}</span>
                ))}
              </div>
            )}

            {/* Web sources from the LLM-enriched explanation */}
            {webSources.length > 0 && (
              <div className="web-sources">
                <p className="web-sources-label">Sources</p>
                {webSources.map((s, i) => (
                  <a key={i} className="web-source-link" href={s.url} target="_blank" rel="noreferrer">
                    <span className="web-source-domain">{s.source}</span>
                    <span className="web-source-title">{s.title}</span>
                  </a>
                ))}
              </div>
            )}
          </>
        )}
      </div>

      {/* Standalone web research results */}
      {showResearch && (
        <div className="research-section">
          <div className="research-header">
            <span className="research-title">Web Research</span>
          </div>
          {researchLoading ? (
            <div className="panel-loading">
              <div className="spinner small" />
              <p className="loading-text">Searching the web...</p>
            </div>
          ) : researchResults.length > 0 ? (
            <div className="research-results">
              {researchResults.map((r, i) => (
                <a key={i} className="research-result" href={r.url} target="_blank" rel="noreferrer">
                  <span className="research-result-domain">{r.source}</span>
                  <span className="research-result-title">{r.title}</span>
                  <span className="research-result-snippet">{r.snippet}</span>
                </a>
              ))}
            </div>
          ) : (
            <p className="research-empty">No web results found for this selection.</p>
          )}
        </div>
      )}
    </div>
  )
}
