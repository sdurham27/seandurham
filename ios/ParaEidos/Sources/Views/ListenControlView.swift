import SwiftUI

struct ListenControlView: View {
    let isListening: Bool
    let audioLevel: Float
    let isProcessing: Bool
    let onToggle: () -> Void

    var body: some View {
        VStack(spacing: 18) {
            // Pulsing mic button
            ZStack {
                if isListening {
                    Circle()
                        .stroke(Color("Accent").opacity(0.35), lineWidth: 2)
                        .frame(width: 110, height: 110)
                        .scaleEffect(isListening ? 1.25 : 1)
                        .opacity(isListening ? 0 : 1)
                        .animation(
                            .easeOut(duration: 1.6).repeatForever(autoreverses: false),
                            value: isListening
                        )
                }

                Button(action: onToggle) {
                    ZStack {
                        Circle()
                            .fill(isListening ? Color("Accent") : Color("Surface"))
                            .frame(width: 88, height: 88)
                            .shadow(color: isListening ? Color("Accent").opacity(0.4) : .clear,
                                    radius: 16, x: 0, y: 4)

                        Image(systemName: isListening ? "stop.fill" : "mic.fill")
                            .font(.system(size: 30))
                            .foregroundColor(isListening ? .white : .secondary)
                    }
                }
                .buttonStyle(ScaleButtonStyle())
            }
            .frame(height: 110)

            // Status label
            Text(isListening ? "Listening…" : "Tap to Start")
                .font(.subheadline.weight(.semibold))
                .foregroundColor(isListening ? Color("Accent") : .secondary)
                .textCase(.uppercase)
                .tracking(1)

            // Audio level bar
            if isListening {
                GeometryReader { geo in
                    ZStack(alignment: .leading) {
                        RoundedRectangle(cornerRadius: 2)
                            .fill(Color.white.opacity(0.07))
                        RoundedRectangle(cornerRadius: 2)
                            .fill(Color("Accent"))
                            .frame(width: geo.size.width * CGFloat(audioLevel))
                            .animation(.linear(duration: 0.1), value: audioLevel)
                    }
                }
                .frame(height: 4)
                .padding(.horizontal, 8)
            }

            // Processing badge
            if isProcessing {
                HStack(spacing: 6) {
                    ProgressView()
                        .scaleEffect(0.7)
                        .tint(Color("Accent"))
                    Text("Extracting tasks…")
                        .font(.caption.weight(.semibold))
                        .foregroundColor(Color("Accent"))
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(Color("Accent").opacity(0.12))
                .clipShape(Capsule())
            }

            if !isListening && !isProcessing {
                Text("Records 20-sec chunks · Whisper + Claude")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
        }
        .padding(24)
        .frame(maxWidth: .infinity)
        .background(Color("Surface"))
        .clipShape(RoundedRectangle(cornerRadius: 20))
    }
}

struct ScaleButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.93 : 1)
            .animation(.spring(response: 0.2), value: configuration.isPressed)
    }
}
