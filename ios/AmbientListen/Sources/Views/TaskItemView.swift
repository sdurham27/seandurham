import SwiftUI

struct TaskItemView: View {
    let task: AmbientTask
    @EnvironmentObject var taskStore: TaskStore

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            // Check button
            Button { taskStore.toggle(task) } label: {
                ZStack {
                    Circle()
                        .stroke(task.done ? typeColor.opacity(0.6) : Color.white.opacity(0.15), lineWidth: 1.5)
                        .frame(width: 24, height: 24)
                    if task.done {
                        Image(systemName: "checkmark")
                            .font(.system(size: 11, weight: .bold))
                            .foregroundColor(typeColor)
                    }
                }
            }
            .buttonStyle(.plain)
            .padding(.top, 1)

            // Content
            VStack(alignment: .leading, spacing: 5) {
                Text(task.text)
                    .font(.subheadline.weight(.medium))
                    .foregroundColor(task.done ? .secondary : .primary)
                    .strikethrough(task.done)
                    .fixedSize(horizontal: false, vertical: true)

                if !task.context.isEmpty {
                    Text(task.context)
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                }

                HStack(spacing: 6) {
                    // Type badge
                    Text(task.type.label)
                        .font(.system(size: 10, weight: .bold))
                        .foregroundColor(typeColor)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(typeColor.opacity(0.12))
                        .clipShape(RoundedRectangle(cornerRadius: 4))

                    // Priority dot
                    Circle()
                        .fill(priorityColor)
                        .frame(width: 6, height: 6)
                }
            }

            Spacer(minLength: 0)

            // Delete
            Button { taskStore.delete(task) } label: {
                Image(systemName: "trash")
                    .font(.system(size: 13))
                    .foregroundColor(.secondary.opacity(0.5))
            }
            .buttonStyle(.plain)
            .padding(.top, 2)
        }
        .padding(14)
        .background(Color("Surface"))
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .opacity(task.done ? 0.5 : 1)
    }

    private var typeColor: Color {
        switch task.type {
        case .task:      return Color("TypeBlue")
        case .follow_up: return Color("TypeYellow")
        case .reminder:  return Color("TypePurple")
        case .note:      return Color("TypeGreen")
        }
    }

    private var priorityColor: Color {
        switch task.priority {
        case .high:   return Color("Accent")
        case .medium: return Color("TypeYellow")
        case .low:    return .secondary
        }
    }
}
