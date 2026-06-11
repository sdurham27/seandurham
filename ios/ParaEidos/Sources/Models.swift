import Foundation

enum TaskType: String, Codable, CaseIterable {
    case task, follow_up, reminder, note

    var label: String {
        switch self {
        case .task:      return "Task"
        case .follow_up: return "Follow Up"
        case .reminder:  return "Reminder"
        case .note:      return "Note"
        }
    }

    var color: String {
        switch self {
        case .task:      return "TypeBlue"
        case .follow_up: return "TypeYellow"
        case .reminder:  return "TypePurple"
        case .note:      return "TypeGreen"
        }
    }
}

enum TaskPriority: String, Codable {
    case high, medium, low
}

struct AmbientTask: Identifiable, Codable, Equatable {
    let id: UUID
    var text: String
    var type: TaskType
    var context: String
    var priority: TaskPriority
    var done: Bool
    var createdAt: Date

    init(text: String, type: TaskType, context: String, priority: TaskPriority) {
        self.id = UUID()
        self.text = text
        self.type = type
        self.context = context
        self.priority = priority
        self.done = false
        self.createdAt = Date()
    }
}
