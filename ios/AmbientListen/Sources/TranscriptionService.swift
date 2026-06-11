import Foundation

struct TranscriptionService {
    enum TranscriptionError: LocalizedError {
        case api(String)
        var errorDescription: String? { if case .api(let m) = self { return m }; return nil }
    }

    // Whisper hallucinates these phrases on near-silent audio
    private static let hallucinations: [String] = [
        "thanks for watching",
        "thank you for watching",
        "please subscribe",
        "like and subscribe",
        "see you next time",
        "don't forget to subscribe",
    ]

    static func transcribe(audioURL: URL, apiKey: String, priorContext: String = "") async throws -> String {
        var request = URLRequest(url: URL(string: "https://api.openai.com/v1/audio/transcriptions")!)
        request.httpMethod = "POST"
        request.setValue("Bearer \(apiKey)", forHTTPHeaderField: "Authorization")

        let boundary = "Boundary-\(UUID().uuidString)"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        let audioData = try Data(contentsOf: audioURL)
        var body = Data()

        func field(_ name: String, _ value: String) {
            body += "--\(boundary)\r\nContent-Disposition: form-data; name=\"\(name)\"\r\n\r\n\(value)\r\n".data(using: .utf8)!
        }

        field("model", "whisper-1")
        field("language", "en")
        field("response_format", "verbose_json")
        // Passing prior context reduces hallucinations and improves continuity
        if !priorContext.isEmpty {
            field("prompt", priorContext)
        }

        body += "--\(boundary)\r\n".data(using: .utf8)!
        body += "Content-Disposition: form-data; name=\"file\"; filename=\"audio.m4a\"\r\n".data(using: .utf8)!
        body += "Content-Type: audio/m4a\r\n\r\n".data(using: .utf8)!
        body += audioData
        body += "\r\n--\(boundary)--\r\n".data(using: .utf8)!

        request.httpBody = body

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            struct Err: Decodable { struct Inner: Decodable { let message: String }; let error: Inner }
            let msg = (try? JSONDecoder().decode(Err.self, from: data))?.error.message ?? "Whisper \((response as? HTTPURLResponse)?.statusCode ?? 0)"
            throw TranscriptionError.api(msg)
        }

        struct Segment: Decodable { let no_speech_prob: Double }
        struct Verbose: Decodable { let text: String; let segments: [Segment] }

        let verbose = try JSONDecoder().decode(Verbose.self, from: data)

        // Discard if the average no_speech probability is too high — it's hallucinating
        if !verbose.segments.isEmpty {
            let avgNoSpeech = verbose.segments.map(\.no_speech_prob).reduce(0, +) / Double(verbose.segments.count)
            if avgNoSpeech > 0.6 { return "" }
        }

        let text = verbose.text.trimmingCharacters(in: .whitespacesAndNewlines)
        let lower = text.lowercased()

        // Drop known hallucination phrases
        if hallucinations.contains(where: { lower.contains($0) }) { return "" }

        return text
    }
}
