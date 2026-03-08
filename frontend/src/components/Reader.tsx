import { useState, useEffect, useCallback } from 'react'
import { getPages, checkNudge, updatePage } from '../services/api'
import ExplanationPanel from './ExplanationPanel'

interface Props {
  sessionId: string
  documentName: string
}

interface PageData {
  page: number
  text: string
}

export default function Reader({ sessionId, documentName }: Props) {
  const [pages, setPages] = useState<PageData[]>([])
  const [currentPage, setCurrentPage] = useState(1)
  const [nudge, setNudge] = useState<string | null>(null)
  const [nudgeDismissed, setNudgeDismissed] = useState(false)
  const [selection, setSelection] = useState<string | null>(null)
  const [showPanel, setShowPanel] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getPages(sessionId).then(data => {
      setPages(data.pages)
      setLoading(false)
    })
  }, [sessionId])

  // Check for nudges when page changes
  useEffect(() => {
    setNudgeDismissed(false)
    checkNudge(sessionId, currentPage).then(data => {
      setNudge(data.nudge)
    })
    updatePage(sessionId, currentPage)
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
    <div className="reader-screen">
      {/* Top bar — minimal */}
      <header className="reader-header">
        <span className="reader-doc-name">{documentName}</span>
        <span className="reader-page-info">
          Page {currentPage} of {pages.length}
        </span>
      </header>

      {/* Nudge — subtle, dismissible */}
      {nudge && !nudgeDismissed && (
        <div className="nudge-bar">
          <span className="nudge-icon">*</span>
          <span className="nudge-text">{nudge}</span>
          <button className="nudge-dismiss" onClick={() => setNudgeDismissed(true)}>
            Got it
          </button>
        </div>
      )}

      {/* Reading area */}
      <main className="reader-body">
        <div
          className="reader-text"
          onMouseUp={handleTextSelect}
        >
          {pageData ? (
            pageData.text.split('\n').map((para, i) => (
              para.trim() ? <p key={i}>{para}</p> : null
            ))
          ) : (
            <p className="empty-page">This page has no extractable text.</p>
          )}
        </div>
      </main>

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

      {/* Explanation panel — slides in from the right */}
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
