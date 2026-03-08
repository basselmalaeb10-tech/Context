import { useState, useRef } from 'react'
import { uploadPdf } from '../services/api'

interface Props {
  onComplete: (data: any) => void
}

export default function Upload({ onComplete }: Props) {
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  async function handleFile(file: File) {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Please upload a PDF file.')
      return
    }
    setError(null)
    setUploading(true)
    try {
      const data = await uploadPdf(file)
      onComplete(data)
    } catch (e: any) {
      setError(e.message || 'Upload failed.')
    } finally {
      setUploading(false)
    }
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  function onFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
  }

  return (
    <div className="upload-screen">
      <div className="upload-content">
        <h1 className="logo">Context</h1>
        <p className="tagline">
          An intelligent reading companion that reveals what you need to know,
          exactly when you need it.
        </p>

        <div
          className={`drop-zone ${dragging ? 'dragging' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          onClick={() => fileRef.current?.click()}
        >
          {uploading ? (
            <div className="upload-progress">
              <div className="spinner" />
              <p>Analyzing document...</p>
            </div>
          ) : (
            <>
              <p className="drop-text">Drop a PDF here, or click to browse</p>
              <p className="drop-hint">Philosophy, economics, research papers, and more</p>
            </>
          )}
        </div>

        {error && <p className="error">{error}</p>}

        <input
          ref={fileRef}
          type="file"
          accept=".pdf"
          onChange={onFileSelect}
          hidden
        />
      </div>
    </div>
  )
}
