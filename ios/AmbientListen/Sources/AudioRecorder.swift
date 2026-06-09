import AVFoundation
import Combine

@MainActor
class AudioRecorder: NSObject, ObservableObject {
    @Published var isRecording = false
    @Published var audioLevel: Float = 0
    @Published var errorMessage: String?

    var onChunk: ((URL) -> Void)?

    private var recorder: AVAudioRecorder?
    private var chunkTimer: Timer?
    private var levelTimer: Timer?
    private var currentChunkURL: URL?

    private let chunkDuration: TimeInterval = 20
    private let silenceThreshold: Float = -45  // dBFS

    // MARK: - Public

    func start() {
        errorMessage = nil
        guard configureSession() else { return }
        startNewChunk()
        startLevelTimer()
        isRecording = true
    }

    func stop() {
        chunkTimer?.invalidate(); chunkTimer = nil
        levelTimer?.invalidate(); levelTimer = nil
        finalizeChunk()
        recorder?.stop(); recorder = nil
        audioLevel = 0
        isRecording = false
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
    }

    // MARK: - Private

    @discardableResult
    private func configureSession() -> Bool {
        do {
            let session = AVAudioSession.sharedInstance()
            // .playAndRecord keeps the session alive in background with UIBackgroundModes:audio
            try session.setCategory(.playAndRecord, mode: .default,
                                    options: [.allowBluetooth, .defaultToSpeaker, .mixWithOthers])
            try session.setActive(true)
            return true
        } catch {
            errorMessage = "Microphone error: \(error.localizedDescription)"
            return false
        }
    }

    private func startNewChunk() {
        let url = tempURL()
        currentChunkURL = url

        // 16 kHz mono AAC — small files, great Whisper accuracy
        let settings: [String: Any] = [
            AVFormatIDKey:            Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey:          16000,
            AVNumberOfChannelsKey:    1,
            AVEncoderAudioQualityKey: AVAudioQuality.medium.rawValue,
            AVEncoderBitRateKey:      32000
        ]

        do {
            recorder = try AVAudioRecorder(url: url, settings: settings)
            recorder?.delegate = self
            recorder?.isMeteringEnabled = true
            recorder?.record()
        } catch {
            errorMessage = "Recording error: \(error.localizedDescription)"
            isRecording = false
            return
        }

        // Schedule end of this chunk
        chunkTimer?.invalidate()
        chunkTimer = Timer.scheduledTimer(withTimeInterval: chunkDuration, repeats: false) { [weak self] _ in
            Task { @MainActor in
                self?.rollChunk()
            }
        }
    }

    private func rollChunk() {
        guard isRecording else { return }
        finalizeChunk()
        startNewChunk()
    }

    private func finalizeChunk() {
        recorder?.stop()
        guard let url = currentChunkURL else { return }
        currentChunkURL = nil

        // Skip near-silent chunks (< 8 KB ≈ no real speech)
        let size = (try? FileManager.default.attributesOfItem(atPath: url.path)[.size] as? Int) ?? 0
        guard size > 8_000 else {
            try? FileManager.default.removeItem(at: url)
            return
        }

        onChunk?(url)
    }

    private func startLevelTimer() {
        levelTimer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] _ in
            guard let r = self?.recorder, r.isRecording else { return }
            r.updateMeters()
            // Normalize from roughly -60..0 dBFS to 0..1
            let db = r.averagePower(forChannel: 0)
            let normalized = max(0, min(1, (db + 60) / 60))
            Task { @MainActor in self?.audioLevel = normalized }
        }
    }

    private func tempURL() -> URL {
        FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString + ".m4a")
    }
}

extension AudioRecorder: AVAudioRecorderDelegate {
    nonisolated func audioRecorderEncodeErrorDidOccur(_ recorder: AVAudioRecorder, error: Error?) {
        Task { @MainActor in
            self.errorMessage = error?.localizedDescription ?? "Encode error"
            self.isRecording = false
        }
    }
}
