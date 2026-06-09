export default function ListenControl({ isListening, level, isProcessing, onToggle }) {
  return (
    <div className="listen-card">
      <div className="mic-ring">
        <div className={`mic-ring-pulse ${isListening ? 'active' : ''}`} />
        <button
          className={`mic-btn ${isListening ? 'listening' : 'idle'}`}
          onClick={onToggle}
          aria-label={isListening ? 'Stop listening' : 'Start listening'}
        >
          {isListening ? <StopIcon /> : <MicIcon />}
        </button>
      </div>

      <div className={`listen-status ${isListening ? 'listening' : ''}`}>
        {isListening ? 'Listening' : 'Tap to Start'}
      </div>

      {isListening && (
        <div className="audio-level" role="progressbar" aria-valuenow={Math.round(level * 100)}>
          <div className="audio-level-bar" style={{ width: `${level * 100}%` }} />
        </div>
      )}

      {isProcessing && (
        <div className="processing-badge">
          <div className="spinner" />
          Extracting tasks…
        </div>
      )}

      {!isListening && !isProcessing && (
        <p className="listen-meta">
          Records in 20-second chunks · sends to Whisper + Claude
        </p>
      )}
    </div>
  )
}

function MicIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2a3 3 0 0 1 3 3v7a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3z"/>
      <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
      <line x1="12" y1="19" x2="12" y2="22"/>
      <line x1="8" y1="22" x2="16" y2="22"/>
    </svg>
  )
}

function StopIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor">
      <rect x="6" y="6" width="12" height="12" rx="2"/>
    </svg>
  )
}
