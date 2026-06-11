import SwiftUI

struct SetupNoticeView: View {
    let onTap: () -> Void

    var body: some View {
        VStack(spacing: 12) {
            Image(systemName: "key.fill")
                .font(.system(size: 28))
                .foregroundColor(Color("Accent"))

            Text("Set up API keys to get started")
                .font(.headline)

            Text("Add your OpenAI and Anthropic keys to enable listening and task extraction.")
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)

            Button("Open Settings", action: onTap)
                .buttonStyle(.borderedProminent)
                .tint(Color("Accent"))
        }
        .padding(24)
        .frame(maxWidth: .infinity)
        .background(Color("Surface"))
        .clipShape(RoundedRectangle(cornerRadius: 20))
    }
}
