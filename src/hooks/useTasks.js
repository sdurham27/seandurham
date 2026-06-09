import { useState, useCallback, useEffect } from 'react'

const STORAGE_KEY = 'ambient_tasks'

function load() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
  } catch {
    return []
  }
}

function save(tasks) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks))
}

export function useTasks() {
  const [tasks, setTasksState] = useState(load)

  const setTasks = useCallback((updater) => {
    setTasksState(prev => {
      const next = typeof updater === 'function' ? updater(prev) : updater
      save(next)
      return next
    })
  }, [])

  const addTasks = useCallback((newItems) => {
    if (!newItems.length) return 0
    setTasks(prev => [...newItems, ...prev])
    return newItems.length
  }, [setTasks])

  const toggleDone = useCallback((id) => {
    setTasks(prev => prev.map(t => t.id === id ? { ...t, done: !t.done } : t))
  }, [setTasks])

  const deleteTask = useCallback((id) => {
    setTasks(prev => prev.filter(t => t.id !== id))
  }, [setTasks])

  const clearDone = useCallback(() => {
    setTasks(prev => prev.filter(t => !t.done))
  }, [setTasks])

  const clearAll = useCallback(() => {
    setTasks([])
  }, [setTasks])

  const activeTasks = tasks.filter(t => !t.done)
  const doneTasks = tasks.filter(t => t.done)

  return { tasks, activeTasks, doneTasks, addTasks, toggleDone, deleteTask, clearDone, clearAll }
}
