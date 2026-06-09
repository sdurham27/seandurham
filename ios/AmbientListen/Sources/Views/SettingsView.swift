import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var settings: AppSettings
    @Environment(\.dismiss) var dismiss

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    LabeledContent("Name") {
                        TextField("e.g. Sean", text: $settings.userName)
                            .multilineTextAlignment(.trailing)
                            .autocorrectionDisabled()
                    }
                } header: {
                    Text("Your Identity")
                } footer: {
                    Text("Helps Claude identify what's relevant to you in conversations.")
                }

                Section {
                    SecureField("sk-…", text: $settings.openAIKey)
                        .font(.system(.body, design: .monospaced))
                        .autocorrectionDisabled()
                        .textInputAutocapitalization(.never)
                } header: {
                    Text("OpenAI API Key (Whisper)")
                } footer: {
                    Text("Used for speech-to-text transcription. Get yours at platform.openai.com")
                }

                Section {
                    SecureField("sk-ant-…", text: $settings.anthropicKey)
                        .font(.system(.body, design: .monospaced))
                        .autocorrectionDisabled()
                        .textInputAutocapitalization(.never)
                } header: {
                    Text("Anthropic API Key (Claude)")
                } footer: {
                    Text("Used for task extraction. Get yours at console.anthropic.com\n\nKeys are stored only on this device.")
                }
            }
            .scrollContentBackground(.hidden)
            .background(Color("Background"))
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                }
            }
        }
        .preferredColorScheme(.dark)
    }
}
