import SwiftUI

struct TaskListView: View {
    @EnvironmentObject var taskStore: TaskStore

    var body: some View {
        VStack(spacing: 10) {
            // Active tasks
            sectionHeader(title: "To Do", count: taskStore.active.count)

            if taskStore.active.isEmpty {
                emptyState
            } else {
                ForEach(taskStore.active) { task in
                    TaskItemView(task: task)
                        .environmentObject(taskStore)
                }
            }

            // Done tasks
            if !taskStore.done.isEmpty {
                HStack {
                    sectionHeader(title: "Done", count: taskStore.done.count)
                    Spacer()
                    Button("Clear") { taskStore.clearDone() }
                        .font(.caption.weight(.semibold))
                        .foregroundColor(.secondary)
                }
                ForEach(taskStore.done) { task in
                    TaskItemView(task: task)
                        .environmentObject(taskStore)
                }
            }
        }
    }

    private func sectionHeader(title: String, count: Int) -> some View {
        HStack {
            Text(title)
                .font(.caption.weight(.bold))
                .foregroundColor(.secondary)
                .textCase(.uppercase)
                .tracking(0.8)
            Text("\(count)")
                .font(.caption.weight(.semibold))
                .foregroundColor(.secondary)
                .padding(.horizontal, 8)
                .padding(.vertical, 2)
                .background(Color("Surface"))
                .clipShape(Capsule())
            Spacer()
        }
        .padding(.horizontal, 4)
    }

    private var emptyState: some View {
        VStack(spacing: 8) {
            Image(systemName: "tray")
                .font(.system(size: 28))
                .foregroundColor(.secondary.opacity(0.4))
            Text("Nothing captured yet")
                .font(.subheadline)
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 32)
    }
}
