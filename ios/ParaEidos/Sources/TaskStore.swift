import Foundation
import Combine

class TaskStore: ObservableObject {
    @Published private(set) var tasks: [AmbientTask] = []

    private let storageKey = "ambient_tasks_v1"

    init() { load() }

    var active: [AmbientTask] { tasks.filter { !$0.done } }
    var done: [AmbientTask]   { tasks.filter {  $0.done } }

    func add(_ newTasks: [AmbientTask]) {
        guard !newTasks.isEmpty else { return }
        tasks.insert(contentsOf: newTasks, at: 0)
        persist()
    }

    func toggle(_ task: AmbientTask) {
        guard let i = tasks.firstIndex(where: { $0.id == task.id }) else { return }
        tasks[i].done.toggle()
        persist()
    }

    func delete(_ task: AmbientTask) {
        tasks.removeAll { $0.id == task.id }
        persist()
    }

    func clearDone() {
        tasks.removeAll { $0.done }
        persist()
    }

    func clearAll() {
        tasks.removeAll()
        persist()
    }

    private func persist() {
        guard let data = try? JSONEncoder().encode(tasks) else { return }
        UserDefaults.standard.set(data, forKey: storageKey)
    }

    private func load() {
        guard let data = UserDefaults.standard.data(forKey: storageKey),
              let saved = try? JSONDecoder().decode([AmbientTask].self, from: data)
        else { return }
        tasks = saved
    }
}
