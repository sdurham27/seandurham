import SwiftUI
import AVFoundation

@main
struct AmbientListenApp: App {
    @StateObject private var settings  = AppSettings()
    @StateObject private var taskStore = TaskStore()

    init() {
        // Configure audio session early so background mode activates cleanly
        try? AVAudioSession.sharedInstance().setCategory(
            .playAndRecord,
            mode: .default,
            options: [.allowBluetooth, .defaultToSpeaker, .mixWithOthers]
        )
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(settings)
                .environmentObject(taskStore)
                .preferredColorScheme(.dark)
        }
    }
}
