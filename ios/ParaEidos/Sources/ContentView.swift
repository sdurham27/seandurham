import SwiftUI

struct ContentView: View {
    @EnvironmentObject var settings:  AppSettings
    @EnvironmentObject var taskStore: TaskStore

    @StateObject private var recorder = AudioRecorder()

    @State private var transcriptChunks: [String] = []
    @State private var isProcessing = false
    @State private var errorMessage: String?
    @State private var showSettings = false
    @State private var toastText: String?
    @State private var toastTask: Task<Void, Never>?

    var body: some View {
        ZStack(alignment: .bottom) {
            Color("Background").ignoresSafeArea()

            VStack(spacing: 0) {
                // Header
                HStack {
                    Text("Ambient").font(.title2.bold()) +
                    Text(".Listen").font(.title2.bold()).foregroundColor(Color("Accent"))
                    Spacer()
                    Button { showSettings = true } label: {
                        Image(systemName: "gearshape.fill")
                            .font(.system(size: 18))
                            .foregroundColor(.secondary)
                    }
                    .padding(8)
                }
                .padding(.horizontal, 20)
                .padding(.top, 8)
                .padding(.bottom, 12)
                .background(Color("Surface"))

                ScrollView {
                    VStack(spacing: 16) {
                        // Setup notice
                        if !settings.isConfigured {
                            SetupNoticeView { showSettings = true }
                        } else {
                            // Mic control
                            ListenControlView(
                                isListening: recorder.isRecording,
                                audioLevel: recorder.audioLevel,
                                isProcessing: isProcessing,
                                onToggle: toggleListening
                            )
                        }

                        // Error
                        if let err = errorMessage ?? recorder.errorMessage {
                            ErrorBanner(message: err)
                        }

                        // Live transcript (collapsible)
                        if !transcriptChunks.isEmpty {
                            TranscriptCard(chunks: transcriptChunks)
                        }

                        // Task list
                        TaskListView()
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 20)
                    .padding(.bottom, 40)
                }
            }

            // Toast
            if let text = toastText {
                Text(text)
                    .font(.subheadline.bold())
                    .foregroundColor(Color("Background"))
                    .padding(.horizontal, 18)
                    .padding(.vertical, 10)
                    .background(Color("TypeGreen"))
                    .clipShape(Capsule())
                    .shadow(radius: 8)
                    .padding(.bottom, 28)
                    .transition(.move(edge: .bottom).combined(with: .opacity))
                    .animation(.spring(response: 0.35), value: toastText)
            }
        }
        .sheet(isPresented: $showSettings) {
            SettingsView()
                .environmentObject(settings)
        }
        .onReceive(recorder.$errorMessage) { msg in
            if msg != nil { errorMessage = msg }
        }
    }

    // MARK: – Actions

    private func toggleListening() {
        guard settings.isConfigured else { showSettings = true; return }

        if recorder.isRecording {
            recorder.stop()
        } else {
            errorMessage = nil
            transcriptChunks = []
            recorder.onChunk = { [weak recorder] url in
                Task { await handleChunk(url: url) }
                // Clean up the temp file after a short delay
                Task {
                    try? await Task.sleep(nanoseconds: 120_000_000_000) // 2 min
                    try? FileManager.default.removeItem(at: url)
                }
            }
            recorder.start()
        }
    }

    private func handleChunk(url: URL) async {
        guard settings.isConfigured else { return }

        do {
            let priorContext = transcriptChunks.last ?? ""
            let text = try await TranscriptionService.transcribe(audioURL: url, apiKey: settings.openAIKey, priorContext: priorContext)
            guard !text.isEmpty else { return }

            await MainActor.run { transcriptChunks.append(text) }

            await MainActor.run { isProcessing = true }
            let newTasks = try await TaskExtractionService.extract(
                transcriptChunks: transcriptChunks,
                existingTasks: taskStore.tasks,
                userName: settings.userName,
                apiKey: settings.anthropicKey
            )
            await MainActor.run {
                isProcessing = false
                if !newTasks.isEmpty {
                    taskStore.add(newTasks)
                    showToast("\(newTasks.count) item\(newTasks.count > 1 ? "s" : "") captured")
                }
            }
        } catch {
            await MainActor.run {
                isProcessing = false
                errorMessage = error.localizedDescription
            }
        }
    }

    private func showToast(_ text: String) {
        toastTask?.cancel()
        withAnimation { toastText = text }
        toastTask = Task {
            try? await Task.sleep(nanoseconds: 3_000_000_000)
            withAnimation { toastText = nil }
        }
    }
}
