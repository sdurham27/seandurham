import { useState } from 'react'

export default function Settings({ config, onSave, onClose }) {
  const [openaiKey, setOpenaiKey] = useState(config.openaiKey || '')
  const [anthropicKey, setAnthropicKey] = useState(config.anthropicKey || '')
  const [userName, setUserName] = useState(config.userName || '')

  const handleSave = () => {
    onSave({ openaiKey: openaiKey.trim(), anthropicKey: anthropicKey.trim(), userName: userName.trim() })
    onClose()
  }

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-sheet" onClick={e => e.stopPropagation()}>
        <div className="settings-title">Settings</div>

        <div className="settings-group">
          <p className="settings-section-title">Your name</p>
          <div className="settings-input-row">
            <label className="settings-label">Name</label>
            <input
              className="settings-name-input"
              type="text"
              placeholder="e.g. Sean"
              value={userName}
              onChange={e => setUserName(e.target.value)}
            />
            <p className="settings-hint">Helps Claude identify what's relevant to you in conversations</p>
          </div>
        </div>

        <div className="divider" />

        <div className="settings-group">
          <p className="settings-section-title">API Keys</p>
          <div className="settings-input-row">
            <label className="settings-label">OpenAI API Key (Whisper)</label>
            <input
              className="settings-input"
              type="password"
              placeholder="sk-..."
              value={openaiKey}
              onChange={e => setOpenaiKey(e.target.value)}
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
            />
            <p className="settings-hint">Used for speech-to-text transcription via Whisper</p>
          </div>

          <div className="settings-input-row">
            <label className="settings-label">Anthropic API Key (Claude)</label>
            <input
              className="settings-input"
              type="password"
              placeholder="sk-ant-..."
              value={anthropicKey}
              onChange={e => setAnthropicKey(e.target.value)}
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
            />
            <p className="settings-hint">Used for intelligent task extraction from transcripts</p>
          </div>
          <p className="settings-hint" style={{ marginTop: 4 }}>
            Keys are stored only in your browser's local storage — never sent to any server other than OpenAI/Anthropic directly.
          </p>
        </div>

        <button className="settings-save-btn" onClick={handleSave}>Save</button>
      </div>
    </div>
  )
}
