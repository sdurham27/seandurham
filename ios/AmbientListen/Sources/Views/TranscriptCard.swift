import SwiftUI

struct TranscriptCard: View {
    let chunks: [String]
    @State private var expanded = false

    var body: some View {
        VStack(spacing: 0) {
            Button {
                withAnimation(.spring(response: 0.3)) { expanded.toggle() }
            } label: {
                HStack {
                    Image(systemName: "waveform")
                        .font(.caption)
                    Text("Live Transcript")
                        .font(.caption.weight(.semibold))
                        .textCase(.uppercase)
                        .tracking(0.8)
                    Spacer()
                    Image(systemName: "chevron.down")
                        .font(.caption)
                        .rotationEffect(.degrees(expanded ? 180 : 0))
                }
                .foregroundColor(.secondary)
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
            }
            .buttonStyle(.plain)

            if expanded {
                Divider().opacity(0.15)
                ScrollView {
                    VStack(alignment: .leading, spacing: 6) {
                        ForEach(Array(chunks.enumerated()), id: \.offset) { i, chunk in
                            Text(chunk)
                                .font(.caption)
                                .foregroundColor(i == chunks.count - 1 ? .primary : .secondary)
                                .frame(maxWidth: .infinity, alignment: .leading)
                        }
                    }
                    .padding(14)
                }
                .frame(maxHeight: 140)
            }
        }
        .background(Color("Surface"))
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }
}
