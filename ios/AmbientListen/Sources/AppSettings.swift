import Foundation
import Combine

class AppSettings: ObservableObject {
    @Published var openAIKey: String    { didSet { save() } }
    @Published var anthropicKey: String { didSet { save() } }
    @Published var userName: String     { didSet { save() } }

    var isConfigured: Bool {
        !openAIKey.isEmpty && !anthropicKey.isEmpty
    }

    init() {
        let d = UserDefaults.standard
        openAIKey    = d.string(forKey: "openai_key")    ?? ""
        anthropicKey = d.string(forKey: "anthropic_key") ?? ""
        userName     = d.string(forKey: "user_name")     ?? ""
    }

    private func save() {
        let d = UserDefaults.standard
        d.set(openAIKey,    forKey: "openai_key")
        d.set(anthropicKey, forKey: "anthropic_key")
        d.set(userName,     forKey: "user_name")
    }
}
