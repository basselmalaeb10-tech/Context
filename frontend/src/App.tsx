import { useState } from 'react'
import Upload from './components/Upload'
import Calibration from './components/Calibration'
import Reader from './components/Reader'

type AppState = 'upload' | 'calibration' | 'reading'

interface SessionData {
  sessionId: string
  documentName: string
  calibrationQuestions: any[]
}

export default function App() {
  const [state, setState] = useState<AppState>('upload')
  const [session, setSession] = useState<SessionData | null>(null)

  function handleUploadComplete(data: any) {
    setSession({
      sessionId: data.session_id,
      documentName: data.document_name,
      calibrationQuestions: data.calibration_questions,
    })
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
      {state === 'calibration' && session && (
        <Calibration
          sessionId={session.sessionId}
          documentName={session.documentName}
          questions={session.calibrationQuestions}
          onComplete={handleCalibrationComplete}
        />
      )}
      {state === 'reading' && session && (
        <Reader
          sessionId={session.sessionId}
          documentName={session.documentName}
        />
      )}
    </div>
  )
}
