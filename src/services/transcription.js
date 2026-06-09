export async function transcribeAudio(blob, mimeType, apiKey) {
  const form = new FormData()
  const ext = mimeType.includes('mp4') || mimeType.includes('m4a') ? 'm4a' : 'webm'
  form.append('file', blob, `audio.${ext}`)
  form.append('model', 'whisper-1')
  form.append('language', 'en')

  const res = await fetch('https://api.openai.com/v1/audio/transcriptions', {
    method: 'POST',
    headers: { Authorization: `Bearer ${apiKey}` },
    body: form,
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err?.error?.message || `Whisper error ${res.status}`)
  }

  const data = await res.json()
  return data.text?.trim() || ''
}
