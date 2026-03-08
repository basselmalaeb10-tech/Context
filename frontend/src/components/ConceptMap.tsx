import { useState } from 'react'

interface ConceptNode {
  id: string
  label: string
  domain: string
  importance: number
  description: string
  source_reference?: string
  is_prerequisite_only?: boolean
}

interface ConceptEdge {
  from: string
  to: string
  label: string
}

interface Props {
  conceptMap: {
    nodes: ConceptNode[]
    edges: ConceptEdge[]
  }
  bookMetadata: any
  onContinue: () => void
}

export default function ConceptMap({ conceptMap, bookMetadata, onContinue }: Props) {
  const [selectedNode, setSelectedNode] = useState<ConceptNode | null>(null)
  const nodes = conceptMap?.nodes || []
  const edges = conceptMap?.edges || []

  // Group nodes: main concepts vs prerequisites
  const mainConcepts = nodes.filter(n => !n.is_prerequisite_only)
  const prereqConcepts = nodes.filter(n => n.is_prerequisite_only)

  // Find connections for a node
  function getConnections(nodeId: string) {
    const dependsOn = edges.filter(e => e.to === nodeId).map(e => e.from)
    const requiredBy = edges.filter(e => e.from === nodeId).map(e => e.to)
    return { dependsOn, requiredBy }
  }

  // Size classes based on importance
  function sizeClass(importance: number) {
    if (importance >= 0.8) return 'node-lg'
    if (importance >= 0.5) return 'node-md'
    return 'node-sm'
  }

  return (
    <div className="concept-map-screen">
      <div className="concept-map-content">
        <h1 className="logo">Context</h1>
        <h2 className="concept-map-title">Knowledge Map</h2>
        <p className="concept-map-subtitle">
          Here are the key concepts in <em>{bookMetadata?.title}</em>.
          Click any concept to learn what it is before you start reading.
        </p>

        <div className="concept-map-layout">
          {/* Main concept cloud */}
          <div className="concept-cloud">
            {mainConcepts.map(node => (
              <button
                key={node.id}
                className={`concept-node ${sizeClass(node.importance)} ${selectedNode?.id === node.id ? 'selected' : ''}`}
                onClick={() => setSelectedNode(node)}
                title={node.description}
              >
                <span className="node-label">{node.label}</span>
                {node.source_reference && (
                  <span className="node-source">{node.source_reference}</span>
                )}
              </button>
            ))}
          </div>

          {/* Prerequisite concepts */}
          {prereqConcepts.length > 0 && (
            <div className="prereq-section">
              <p className="prereq-heading">Background knowledge</p>
              <div className="prereq-cloud">
                {prereqConcepts.map(node => (
                  <button
                    key={node.id}
                    className={`concept-node prereq ${selectedNode?.id === node.id ? 'selected' : ''}`}
                    onClick={() => setSelectedNode(node)}
                  >
                    {node.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Detail panel */}
          {selectedNode && (
            <div className="concept-detail">
              <div className="concept-detail-header">
                <h3>{selectedNode.label}</h3>
                <button className="panel-close" onClick={() => setSelectedNode(null)}>&times;</button>
              </div>
              {selectedNode.source_reference && (
                <p className="concept-source">From: {selectedNode.source_reference}</p>
              )}
              <p className="concept-description">
                {selectedNode.description || 'This concept will be explored in the book.'}
              </p>
              <p className="concept-domain">Domain: {selectedNode.domain}</p>
              {(() => {
                const conn = getConnections(selectedNode.id)
                return (
                  <>
                    {conn.dependsOn.length > 0 && (
                      <div className="concept-connections">
                        <span className="connection-label">Builds on: </span>
                        {conn.dependsOn.map(id => (
                          <span
                            key={id}
                            className="concept-tag clickable"
                            onClick={() => {
                              const n = nodes.find(n => n.id === id)
                              if (n) setSelectedNode(n)
                            }}
                          >
                            {id}
                          </span>
                        ))}
                      </div>
                    )}
                    {conn.requiredBy.length > 0 && (
                      <div className="concept-connections">
                        <span className="connection-label">Leads to: </span>
                        {conn.requiredBy.map(id => (
                          <span
                            key={id}
                            className="concept-tag clickable"
                            onClick={() => {
                              const n = nodes.find(n => n.id === id)
                              if (n) setSelectedNode(n)
                            }}
                          >
                            {id}
                          </span>
                        ))}
                      </div>
                    )}
                  </>
                )
              })()}
            </div>
          )}
        </div>

        <button className="next-btn" onClick={onContinue}>
          Continue to Familiarity Check
        </button>
      </div>
    </div>
  )
}
