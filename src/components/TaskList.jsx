import TaskItem from './TaskItem.jsx'

export default function TaskList({ activeTasks, doneTasks, onToggle, onDelete, onClearDone }) {
  return (
    <>
      <div className="task-section">
        <div className="task-section-header">
          <span className="task-section-title">To Do</span>
          <span className="task-count-badge">{activeTasks.length}</span>
        </div>

        {activeTasks.length === 0 ? (
          <div className="task-empty">
            <InboxIcon />
            Nothing captured yet — start listening to build your list
          </div>
        ) : (
          activeTasks.map(task => (
            <TaskItem key={task.id} task={task} onToggle={onToggle} onDelete={onDelete} />
          ))
        )}
      </div>

      {doneTasks.length > 0 && (
        <div className="task-section">
          <div className="task-section-header">
            <span className="task-section-title">Done</span>
            <button className="clear-btn" onClick={onClearDone}>Clear</button>
          </div>
          {doneTasks.map(task => (
            <TaskItem key={task.id} task={task} onToggle={onToggle} onDelete={onDelete} />
          ))}
        </div>
      )}
    </>
  )
}

function InboxIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/>
      <path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>
    </svg>
  )
}
