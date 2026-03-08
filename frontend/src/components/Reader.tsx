import { useState, useEffect, useCallback } from 'react'
import { getPages, checkNudge, updatePage, getPageConcepts } from '../services/api'
import ExplanationPanel from './ExplanationPanel'

interface Props {
  sessionId: string
  documentName: string
}

interface PageData {
  page: number
  text: string
}

interface PageConcept {
  name: string
  is_known_concept: boolean
  needs_explanation: boolean
  explanation_hint: string
  type: string
}

export default function Reader({ sessionId, documentName }: Props) {
  const [pages, setPages] = useState<PageData[]>([])
  const [currentPage, setCurrentPage] = useState(1)
  const [nudge, setNudge] = useState<string | null>(null)
  const [nudgeDismissed, setNudgeDismissed] = useState(false)
  const [selection, setSelection] = useState<string | null>(null)
  const [showPanel, setShowPanel] = useState(false)
  const [loading, setLoading] = useState(true)
  const [pageConcepts, setPageConcepts] = useState<PageConcept[]>([])
  const [conceptsLoading, setConceptsLoading] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)

  useEffect(() => {
    getPages(sessionId).then(data => {
      setPages(data.pages)
      setLoading(false)
    })
  }, [sessionId])

  // Check for nudges and load page concepts when page changes
  useEffect(() => {
    setNudgeDismissed(false)
    checkNudge(sessionId, currentPage).then(data => {
      setNudge(data.nudge)
    })
    updatePage(sessionId, currentPage)

    // Load page-specific concepts for sidebar
    setConceptsLoading(true)
    getPageConcepts(sessionId, currentPage).then(data => {
      setPageConcepts(data.concepts || [])
      setConceptsLoading(false)
    }).catch(() => setConceptsLoading(false))
  }, [sessionId, currentPage])

  const handleTextSelect = useCallback(() => {
    const sel = window.getSelection()
    const text = sel?.toString().trim()
    if (text && text.length > 3) {
      setSelection(text)
      setShowPanel(true)
    }
  }, [])

  function goToPage(page: number) {
    if (page >= 1 && page <= pages.length) {
      setCurrentPage(page)
      setSelection(null)
      setShowPanel(false)
    }
  }

  function handleConceptClick(concept: PageConcept) {
    setSelection(concept.name)
    setShowPanel(true)
  }

  const pageData = pages[currentPage - 1]

  if (loading) {
    return (
      <div className="reader-loading">
        <div className="spinner" />
        <p>Loading document...</p>
      </div>
    )
  }

  return (
    <div className={`reader-screen ${sidebarOpen ? 'with-sidebar' : ''}`}>
      {/* Top bar */}
      <header className="reader-header">
        <span className="reader-doc-name">{documentName}</span>
        <div className="reader-header-right">
          <button
            className="sidebar-toggle"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            title={sidebarOpen ? 'Hide concepts' : 'Show concepts'}
          >
            {sidebarOpen ? 'Hide Concepts' : 'Show Concepts'}
          </button>
          <span className="reader-page-info">
            Page {currentPage} of {pages.length}
          </span>
        </div>
      </header>

      {/* Nudge */}
      {nudge && !nudgeDismissed && (
        <div className="nudge-bar">
          <span className="nudge-icon">*</span>
          <span className="nudge-text">{nudge}</span>
          <button className="nudge-dismiss" onClick={() => setNudgeDismissed(true)}>
            Got it
          </button>
        </div>
      )}

      <div className="reader-layout">
        {/* Reading area */}
        <main className="reader-body">
          <div className="reader-text" onMouseUp={handleTextSelect}>
            {pageData ? (
              renderPageText(pageData.text)
            ) : (
              <p className="empty-page">This page has no extractable text.</p>
            )}
          </div>
        </main>

        {/* Concept sidebar */}
        {sidebarOpen && (
          <aside className="concept-sidebar">
            <div className="sidebar-header">
              <h3>Concepts on this page</h3>
            </div>
            <div className="sidebar-concepts">
              {conceptsLoading ? (
                <div className="sidebar-loading">
                  <div className="spinner small" />
                </div>
              ) : pageConcepts.length > 0 ? (
                pageConcepts.map((concept, i) => (
                  <button
                    key={i}
                    className={`sidebar-concept ${concept.needs_explanation ? 'needs-explanation' : ''}`}
                    onClick={() => handleConceptClick(concept)}
                  >
                    <span className="sidebar-concept-name">
                      {concept.name}
                      <span className={`concept-type-badge type-${concept.type}`}>
                        {concept.type}
                      </span>
                    </span>
                    <span className="sidebar-concept-hint">{concept.explanation_hint}</span>
                  </button>
                ))
              ) : (
                <p className="sidebar-empty">No special concepts on this page.</p>
              )}
            </div>
          </aside>
        )}
      </div>

      {/* Page navigation */}
      <footer className="reader-footer">
        <button
          className="page-btn"
          disabled={currentPage <= 1}
          onClick={() => goToPage(currentPage - 1)}
        >
          Previous
        </button>
        <button
          className="page-btn"
          disabled={currentPage >= pages.length}
          onClick={() => goToPage(currentPage + 1)}
        >
          Next
        </button>
      </footer>

      {/* Explanation panel */}
      {showPanel && selection && (
        <ExplanationPanel
          sessionId={sessionId}
          selectedText={selection}
          surroundingText={pageData?.text || ''}
          page={currentPage}
          onClose={() => { setShowPanel(false); setSelection(null) }}
        />
      )}
    </div>
  )
}

/**
 * Render page text with proper paragraph handling.
 * Groups lines into real paragraphs instead of breaking on every newline.
 */
function renderPageText(text: string) {
  // Split on double-newlines for real paragraph breaks
  const paragraphs = text.split(/\n\s*\n/)

  return paragraphs.map((para, i) => {
    // Within a paragraph, join single newlines with spaces
    // This prevents mid-sentence line breaks from the PDF extraction
    const cleaned = para
      .split('\n')
      .map(line => line.trim())
      .filter(line => line.length > 0)
      .join(' ')

    if (!cleaned) return null

    return <p key={i}>{cleaned}</p>
  })
}
