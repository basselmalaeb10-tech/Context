import { useState } from 'react'
import Upload from './components/Upload'
import MetadataConfirm from './components/MetadataConfirm'
import ConceptMap from './components/ConceptMap'
import Calibration from './components/Calibration'
import Reader from './components/Reader'

type AppState = 'upload' | 'confirm' | 'concept_map' | 'calibration' | 'reading'

interface SessionData {
  sessionId: string
  documentName: string
  bookMetadata: any
  conceptMap: any
  calibrationQuestions: any[]
}

export default function App() {
  const [state, setState] = useState<AppState>('upload')
  const [session, setSession] = useState<SessionData | null>(null)

  function handleUploadComplete(data: any) {
    setSession({
      sessionId: data.session_id,
      documentName: data.document_name,
      bookMetadata: data.book_metadata,
      conceptMap: null,
      calibrationQuestions: [],
    })
    setState('confirm')
  }

  function handleMetadataConfirmed(data: any) {
    setSession(prev => prev ? {
      ...prev,
      bookMetadata: data.book_metadata,
      conceptMap: data.concept_map,
      calibrationQuestions: data.calibration_questions,
    } : null)
    setState('concept_map')
  }

  function handleConceptMapDone() {
    setState('calibration')
  }

  function handleCalibrationComplete() {
    setState('reading')
  }

  return (
    <div className="app">
      {state === 'upload' && (
        <Upload onComplete={handleUploadComplete} />
      )}
      {state === 'confirm' && session && (
        <MetadataConfirm
          sessionId={session.sessionId}
          metadata={session.bookMetadata}
          onConfirmed={handleMetadataConfirmed}
        />
      )}
      {state === 'concept_map' && session && (
        <ConceptMap
          conceptMap={session.conceptMap}
          bookMetadata={session.bookMetadata}
          onContinue={handleConceptMapDone}
        />
      )}
      {state === 'calibration' && session && (
        <Calibration
          sessionId={session.sessionId}
          documentName={session.bookMetadata?.title || session.documentName}
          questions={session.calibrationQuestions}
          onComplete={handleCalibrationComplete}
        />
      )}
      {state === 'reading' && session && (
        <Reader
          sessionId={session.sessionId}
          documentName={session.bookMetadata?.title || session.documentName}
        />
      )}
    </div>
  )
}
