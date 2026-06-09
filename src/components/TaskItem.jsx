export default function TaskItem({ task, onToggle, onDelete }) {
  return (
    <div className={`task-item ${task.done ? 'done' : ''}`}>
      <button className="task-check" onClick={() => onToggle(task.id)} aria-label="Mark done">
        <CheckIcon />
      </button>

      <div className="task-body">
        <div className="task-text">{task.text}</div>
        {task.context && <div className="task-context">{task.context}</div>}
        <div className="task-footer">
          <span className={`task-type-badge badge-${task.type}`}>
            {TYPE_LABELS[task.type] || task.type}
          </span>
          <span className={`priority-dot priority-${task.priority}`} title={task.priority} />
        </div>
      </div>

      <button className="task-delete" onClick={() => onDelete(task.id)} aria-label="Delete">
        <TrashIcon />
      </button>
    </div>
  )
}

const TYPE_LABELS = {
  task: 'Task',
  follow_up: 'Follow up',
  reminder: 'Reminder',
  note: 'Note',
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12"/>
    </svg>
  )
}

function TrashIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="3 6 5 6 21 6"/>
      <path d="M19 6l-1 14H6L5 6"/>
      <path d="M10 11v6M14 11v6"/>
      <path d="M9 6V4h6v2"/>
    </svg>
  )
}
