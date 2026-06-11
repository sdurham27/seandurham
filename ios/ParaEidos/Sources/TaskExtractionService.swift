import Foundation

struct TaskExtractionService {
    enum ExtractionError: LocalizedError {
        case api(String)
        var errorDescription: String? { if case .api(let m) = self { return m }; return nil }
    }

    private struct ExtractedItem: Decodable {
        let text: String
        let type: String
        let context: String
        let priority: String
    }

    static func extract(
        transcriptChunks: [String],
        existingTasks: [AmbientTask],
        userName: String,
        apiKey: String
    ) async throws -> [AmbientTask] {
        let transcript = transcriptChunks.suffix(4).joined(separator: "\n---\n")
        let existingList = existingTasks.isEmpty
            ? "(none yet)"
            : existingTasks.prefix(20).map { "- \($0.text)" }.joined(separator: "\n")

        let nameClause = userName.isEmpty ? "" : "The user's name is \(userName). "

        let system = """
        You monitor conversation transcripts and extract actionable items for the user.
        Only extract items clearly relevant to the user: tasks assigned to them, follow-ups they should make, \
        reminders, or things they should pay attention to. Be concise. Never duplicate existing tasks.
        """

        let userMessage = """
        \(nameClause)Recent conversation transcript:
        \(transcript)

        Already captured (do not duplicate):
        \(existingList)

        Return ONLY a raw JSON array — no markdown, no explanation:
        [{"text":"brief action","type":"task|follow_up|reminder|note","context":"why relevant","priority":"high|medium|low"}]
        If nothing to add, return: []
        """

        let payload: [String: Any] = [
            "model":      "claude-sonnet-4-6",
            "max_tokens": 1024,
            "system":     system,
            "messages":   [["role": "user", "content": userMessage]]
        ]

        var request = URLRequest(url: URL(string: "https://api.anthropic.com/v1/messages")!)
        request.httpMethod = "POST"
        request.setValue(apiKey,           forHTTPHeaderField: "x-api-key")
        request.setValue("2023-06-01",     forHTTPHeaderField: "anthropic-version")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: payload)

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            struct Err: Decodable { struct Inner: Decodable { let message: String }; let error: Inner }
            let msg = (try? JSONDecoder().decode(Err.self, from: data))?.error.message ?? "Claude \((response as? HTTPURLResponse)?.statusCode ?? 0)"
            throw ExtractionError.api(msg)
        }

        struct Claude: Decodable {
            struct Block: Decodable { let text: String }
            let content: [Block]
        }
        let claude = try JSONDecoder().decode(Claude.self, from: data)
        var raw = claude.content.first?.text.trimmingCharacters(in: .whitespacesAndNewlines) ?? "[]"

        // Strip optional markdown fences
        if raw.hasPrefix("```") {
            raw = raw
                .components(separatedBy: "\n")
                .dropFirst()
                .dropLast()
                .joined(separator: "\n")
        }

        guard let jsonData = raw.data(using: .utf8),
              let items = try? JSONDecoder().decode([ExtractedItem].self, from: jsonData)
        else { return [] }

        return items.compactMap { item in
            guard let type = TaskType(rawValue: item.type) else { return nil }
            let priority = TaskPriority(rawValue: item.priority) ?? .medium
            return AmbientTask(text: item.text, type: type, context: item.context, priority: priority)
        }
    }
}
