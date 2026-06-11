// Whisper hallucinates these on near-silent audio (trained on YouTube)
const HALLUCINATIONS = [
  'thanks for watching',
  'thank you for watching',
  'please subscribe',
  'like and subscribe',
  'see you next time',
  "don't forget to subscribe",
]

export async function transcribeAudio(blob, mimeType, apiKey, priorContext = '') {
  const form = new FormData()
  const ext = mimeType.includes('mp4') || mimeType.includes('m4a') ? 'm4a' : 'webm'
  form.append('file', blob, `audio.${ext}`)
  form.append('model', 'whisper-1')
  form.append('language', 'en')
  form.append('response_format', 'verbose_json')
  // Prior context reduces hallucinations and improves word continuity
  if (priorContext) form.append('prompt', priorContext)

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

  // Discard if average no_speech_prob is too high — Whisper is hallucinating
  if (data.segments?.length) {
    const avg = data.segments.reduce((s, seg) => s + (seg.no_speech_prob ?? 0), 0) / data.segments.length
    if (avg > 0.6) return ''
  }

  const text = data.text?.trim() || ''
  const lower = text.toLowerCase()

  // Drop known hallucination phrases
  if (HALLUCINATIONS.some(h => lower.includes(h))) return ''

  return text
}
