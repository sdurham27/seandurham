import { useState, useCallback, useRef } from 'react'
import { useAudioCapture } from './hooks/useAudioCapture.js'
import { useTasks } from './hooks/useTasks.js'
import { transcribeAudio } from './services/transcription.js'
import { extractTasks } from './services/taskExtractor.js'
import ListenControl from './components/ListenControl.jsx'
import TranscriptView from './components/TranscriptView.jsx'
import TaskList from './components/TaskList.jsx'
import Settings from './components/Settings.jsx'

const CONFIG_KEY = 'ambient_config'

function loadConfig() {
  try {
    return JSON.parse(localStorage.getItem(CONFIG_KEY) || '{}')
  } catch {
    return {}
  }
}

export default function App() {
  const [config, setConfig] = useState(loadConfig)
  const [showSettings, setShowSettings] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [transcriptChunks, setTranscriptChunks] = useState([])
  const [error, setError] = useState(null)
  const [toast, setToast] = useState(null)
  const toastTimerRef = useRef(null)
  const chunksSinceExtract = useRef(0)

  const { tasks, activeTasks, doneTasks, addTasks, toggleDone, deleteTask, clearDone } = useTasks()

  const showToast = useCallback((msg) => {
    setToast(msg)
    clearTimeout(toastTimerRef.current)
    toastTimerRef.current = setTimeout(() => setToast(null), 3000)
  }, [])

  const handleChunk = useCallback(async (blob, mimeType) => {
    if (!config.openaiKey || !config.anthropicKey) return
    setError(null)

    try {
      // Transcribe
      const text = await transcribeAudio(blob, mimeType, config.openaiKey)
      if (!text) return

      setTranscriptChunks(prev => {
        const next = [...prev, text].slice(-10)
        return next
      })

      // Extract tasks after every 1-2 chunks (balance cost vs latency)
      chunksSinceExtract.current++
      if (chunksSinceExtract.current < 1) return
      chunksSinceExtract.current = 0

      setIsProcessing(true)
      setTranscriptChunks(prev => {
        extractTasks(prev, tasks, config.userName, config.anthropicKey)
          .then(newItems => {
            const added = addTasks(newItems)
            if (added > 0) showToast(`${added} new item${added > 1 ? 's' : ''} captured`)
          })
          .catch(err => setError(err.message))
          .finally(() => setIsProcessing(false))
        return prev
      })
    } catch (err) {
      setError(err.message)
      setIsProcessing(false)
    }
  }, [config, tasks, addTasks, showToast])

  const { isListening, level, error: micError, startListening, stopListening } =
    useAudioCapture({ onChunk: handleChunk })

  const handleToggle = useCallback(() => {
    if (!config.openaiKey || !config.anthropicKey) {
      setShowSettings(true)
      return
    }
    if (isListening) {
      stopListening()
    } else {
      setTranscriptChunks([])
      startListening()
    }
  }, [config, isListening, startListening, stopListening])

  const handleSaveConfig = useCallback((newConfig) => {
    setConfig(newConfig)
    localStorage.setItem(CONFIG_KEY, JSON.stringify(newConfig))
  }, [])

  const needsSetup = !config.openaiKey || !config.anthropicKey
  const displayError = micError || error

  return (
    <>
      <header className="header">
        <div className="header-title">
          Ambient<span>.</span>Listen
        </div>
        <button className="icon-btn" onClick={() => setShowSettings(true)} aria-label="Settings">
          <GearIcon />
        </button>
      </header>

      <main className="main">
        {needsSetup ? (
          <div className="setup-notice">
            <strong>Set up your API keys to get started</strong>
            Add your OpenAI and Anthropic keys to enable listening and task extraction.
            <button onClick={() => setShowSettings(true)}>Open Settings</button>
          </div>
        ) : (
          <ListenControl
            isListening={isListening}
            level={level}
            isProcessing={isProcessing}
            onToggle={handleToggle}
          />
        )}

        {displayError && (
          <div className="error-banner">{displayError}</div>
        )}

        <TranscriptView chunks={transcriptChunks} />

        <TaskList
          activeTasks={activeTasks}
          doneTasks={doneTasks}
          onToggle={toggleDone}
          onDelete={deleteTask}
          onClearDone={clearDone}
        />
      </main>

      {showSettings && (
        <Settings
          config={config}
          onSave={handleSaveConfig}
          onClose={() => setShowSettings(false)}
        />
      )}

      {toast && <div className="new-tasks-toast">{toast}</div>}
    </>
  )
}

function GearIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3"/>
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
    </svg>
  )
}
