import { useState } from 'react'
import { confirmMetadata } from '../services/api'

interface Props {
  sessionId: string
  metadata: {
    title: string
    author: string
    subtitle?: string
    summary?: string
    domain?: string
  }
  onConfirmed: (data: any) => void
}

export default function MetadataConfirm({ sessionId, metadata, onConfirmed }: Props) {
  const [title, setTitle] = useState(metadata.title || '')
  const [author, setAuthor] = useState(metadata.author || '')
  const [analyzing, setAnalyzing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleConfirm() {
    setAnalyzing(true)
    setError(null)
    try {
      const data = await confirmMetadata(sessionId, title, author)
      onConfirmed(data)
    } catch (e: any) {
      setError(e.message || 'Analysis failed.')
      setAnalyzing(false)
    }
  }

  if (analyzing) {
    return (
      <div className="confirm-screen">
        <div className="confirm-content">
          <h1 className="logo">Context</h1>
          <div className="analyzing-state">
            <div className="spinner" />
            <h2 className="analyzing-title">Analyzing your book</h2>
            <p className="analyzing-detail">
              Identifying key concepts, building knowledge map, and preparing
              personalized calibration questions...
            </p>
            <div className="analyzing-steps">
              <p>Extracting concepts and references</p>
              <p>Mapping prerequisite knowledge</p>
              <p>Generating calibration questions</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="confirm-screen">
      <div className="confirm-content">
        <h1 className="logo">Context</h1>
        <h2 className="confirm-title">Is this your book?</h2>
        <p className="confirm-subtitle">
          We detected the following details. Please confirm or correct them.
        </p>

        <div className="confirm-form">
          <div className="form-group">
            <label className="form-label">Title</label>
            <input
              className="form-input"
              type="text"
              value={title}
              onChange={e => setTitle(e.target.value)}
            />
          </div>
          <div className="form-group">
            <label className="form-label">Author</label>
            <input
              className="form-input"
              type="text"
              value={author}
              onChange={e => setAuthor(e.target.value)}
            />
          </div>
          {metadata.subtitle && (
            <div className="form-group">
              <label className="form-label">Subtitle</label>
              <p className="form-static">{metadata.subtitle}</p>
            </div>
          )}
          {metadata.summary && (
            <div className="form-group">
              <label className="form-label">About this book</label>
              <p className="form-static">{metadata.summary}</p>
            </div>
          )}
          {metadata.domain && (
            <div className="form-group">
              <label className="form-label">Domain</label>
              <span className="domain-badge">{metadata.domain}</span>
            </div>
          )}
        </div>

        {error && <p className="error">{error}</p>}

        <button className="next-btn" onClick={handleConfirm}>
          Confirm &amp; Analyze
        </button>
      </div>
    </div>
  )
}
