import { useState } from 'react'
import { submitCalibration } from '../services/api'

interface Question {
  id: string
  concept_name: string
  question: string
  options: string[]
}

interface Props {
  sessionId: string
  documentName: string
  questions: Question[]
  onComplete: () => void
}

export default function Calibration({ sessionId, documentName, questions, onComplete }: Props) {
  const [answers, setAnswers] = useState<Record<string, number>>({})
  const [currentIdx, setCurrentIdx] = useState(0)
  const [submitting, setSubmitting] = useState(false)

  const question = questions[currentIdx]
  const isLast = currentIdx === questions.length - 1
  const hasAnswer = answers[question?.id] !== undefined

  function selectOption(level: number) {
    setAnswers(prev => ({ ...prev, [question.id]: level }))
  }

  async function handleNext() {
    if (isLast) {
      setSubmitting(true)
      try {
        await submitCalibration(sessionId, answers)
        onComplete()
      } catch {
        setSubmitting(false)
      }
    } else {
      setCurrentIdx(prev => prev + 1)
    }
  }

  if (!question) return null

  return (
    <div className="calibration-screen">
      <div className="calibration-content">
        <p className="calibration-doc">{documentName}</p>
        <h2 className="calibration-title">Quick familiarity check</h2>
        <p className="calibration-subtitle">
          Help us tailor explanations to your level.
          This takes about 30 seconds.
        </p>

        <div className="calibration-progress">
          {questions.map((_, i) => (
            <div
              key={i}
              className={`progress-dot ${i === currentIdx ? 'active' : ''} ${i < currentIdx ? 'done' : ''}`}
            />
          ))}
        </div>

        <div className="question-card">
          <p className="question-text">{question.question}</p>
          <div className="options">
            {question.options.map((opt, i) => (
              <button
                key={i}
                className={`option-btn ${answers[question.id] === i ? 'selected' : ''}`}
                onClick={() => selectOption(i)}
              >
                {opt}
              </button>
            ))}
          </div>
        </div>

        <button
          className="next-btn"
          disabled={!hasAnswer || submitting}
          onClick={handleNext}
        >
          {submitting ? 'Setting up...' : isLast ? 'Start Reading' : 'Next'}
        </button>
      </div>
    </div>
  )
}
