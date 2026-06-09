import { useState } from 'react'

export default function TranscriptView({ chunks }) {
  const [open, setOpen] = useState(false)
  if (!chunks.length) return null

  return (
    <div className="transcript-card">
      <div className="transcript-header" onClick={() => setOpen(o => !o)}>
        <div className="transcript-header-left">
          <WaveIcon />
          Live transcript
        </div>
        <svg className={`chevron ${open ? 'open' : ''}`} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="6 9 12 15 18 9"/>
        </svg>
      </div>
      {open && (
        <div className="transcript-body">
          {chunks.map((text, i) => <p key={i}>{text}</p>)}
        </div>
      )}
    </div>
  )
}

function WaveIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M2 12h2M6 8v8M10 4v16M14 8v8M18 6v12M22 12h-2"/>
    </svg>
  )
}
