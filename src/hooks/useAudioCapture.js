import { useRef, useState, useCallback, useEffect } from 'react'

const CHUNK_MS = 20_000   // 20-second recording chunks
const SILENCE_THRESHOLD = 0.008  // RMS below this = silence

export function useAudioCapture({ onChunk }) {
  const [isListening, setIsListening] = useState(false)
  const [level, setLevel] = useState(0)
  const [error, setError] = useState(null)

  const streamRef = useRef(null)
  const recorderRef = useRef(null)
  const chunksRef = useRef([])
  const audioCtxRef = useRef(null)
  const analyserRef = useRef(null)
  const levelRafRef = useRef(null)
  const mimeTypeRef = useRef('audio/webm')

  const stopLevelMonitor = useCallback(() => {
    if (levelRafRef.current) cancelAnimationFrame(levelRafRef.current)
    levelRafRef.current = null
    setLevel(0)
  }, [])

  const startLevelMonitor = useCallback((stream) => {
    audioCtxRef.current = new AudioContext()
    analyserRef.current = audioCtxRef.current.createAnalyser()
    analyserRef.current.fftSize = 256
    const source = audioCtxRef.current.createMediaStreamSource(stream)
    source.connect(analyserRef.current)

    const buf = new Float32Array(analyserRef.current.fftSize)
    const tick = () => {
      analyserRef.current.getFloatTimeDomainData(buf)
      let sum = 0
      for (const v of buf) sum += v * v
      const rms = Math.sqrt(sum / buf.length)
      setLevel(Math.min(rms / 0.15, 1))
      levelRafRef.current = requestAnimationFrame(tick)
    }
    levelRafRef.current = requestAnimationFrame(tick)
  }, [])

  const flushChunk = useCallback(() => {
    if (!recorderRef.current || chunksRef.current.length === 0) return

    const blob = new Blob(chunksRef.current, { type: mimeTypeRef.current })
    chunksRef.current = []

    // Skip silent chunks (very small blobs = near-silence)
    if (blob.size < 3000) return

    // Quick RMS check via analyser
    if (analyserRef.current) {
      const buf = new Float32Array(analyserRef.current.fftSize)
      analyserRef.current.getFloatTimeDomainData(buf)
      let sum = 0
      for (const v of buf) sum += v * v
      const rms = Math.sqrt(sum / buf.length)
      if (rms < SILENCE_THRESHOLD) return
    }

    onChunk(blob, mimeTypeRef.current)
  }, [onChunk])

  const startListening = useCallback(async () => {
    setError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false })
      streamRef.current = stream

      startLevelMonitor(stream)

      // Pick best supported mime type
      const mimes = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg']
      mimeTypeRef.current = mimes.find(m => MediaRecorder.isTypeSupported(m)) || ''

      const startRecorder = () => {
        chunksRef.current = []
        const recorder = new MediaRecorder(stream, {
          mimeType: mimeTypeRef.current || undefined,
        })
        recorderRef.current = recorder

        recorder.ondataavailable = (e) => {
          if (e.data.size > 0) chunksRef.current.push(e.data)
        }

        recorder.onstop = () => {
          flushChunk()
          // Auto-restart if stream still active
          if (streamRef.current?.active) startRecorder()
        }

        recorder.start()
        setTimeout(() => {
          if (recorder.state === 'recording') recorder.stop()
        }, CHUNK_MS)
      }

      startRecorder()
      setIsListening(true)
    } catch (err) {
      setError(err.message || 'Microphone access denied')
    }
  }, [startLevelMonitor, flushChunk])

  const stopListening = useCallback(() => {
    if (recorderRef.current?.state === 'recording') {
      recorderRef.current.stop()
    }
    streamRef.current?.getTracks().forEach(t => t.stop())
    streamRef.current = null

    if (audioCtxRef.current) {
      audioCtxRef.current.close()
      audioCtxRef.current = null
    }

    stopLevelMonitor()
    setIsListening(false)
  }, [stopLevelMonitor])

  // Cleanup on unmount
  useEffect(() => () => stopListening(), [stopListening])

  return { isListening, level, error, startListening, stopListening }
}
