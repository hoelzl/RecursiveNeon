/**
 * Task List App - Manage tasks and subtasks across multiple lists
 */
import { useState, useEffect } from 'react';
import { useWebSocket } from '../../contexts/WebSocketContext';
import { AppAPI } from '../../utils/appApi';
import { TaskList, Task } from '../../types';

export function TaskListApp() {
  const wsClient = useWebSocket();
  const api = new AppAPI(wsClient);

  const [lists, setLists] = useState<TaskList[]>([]);
  const [selectedList, setSelectedList] = useState<TaskList | null>(null);
  const [newTaskTitle, setNewTaskTitle] = useState('');

  useEffect(() => {
    loadLists();
  }, []);

  const loadLists = async () => {
    try {
      const taskLists = await api.getTaskLists();
      setLists(taskLists);
      if (taskLists.length > 0) {
        setSelectedList(taskLists[0]);
      }
    } catch (error) {
      console.error('Failed to load task lists:', error);
    }
  };

  const handleNewList = async () => {
    const name = prompt('Enter list name:');
    if (!name) return;
    try {
      const newList = await api.createTaskList(name);
      setLists([...lists, newList]);
      setSelectedList(newList);
    } catch (error) {
      console.error('Failed to create list:', error);
    }
  };

  const handleAddTask = async () => {
    if (!selectedList || !newTaskTitle.trim()) return;
    try {
      const newTask = await api.createTask(selectedList.id, {
        title: newTaskTitle,
        completed: false,
      });
      const updated = { ...selectedList, tasks: [...selectedList.tasks, newTask] };
      setSelectedList(updated);
      setLists(lists.map((l) => (l.id === updated.id ? updated : l)));
      setNewTaskTitle('');
    } catch (error) {
      console.error('Failed to add task:', error);
    }
  };

  const handleToggleTask = async (task: Task) => {
    if (!selectedList) return;
    try {
      await api.updateTask(selectedList.id, task.id, { completed: !task.completed });
      const updated = {
        ...selectedList,
        tasks: selectedList.tasks.map((t) =>
          t.id === task.id ? { ...t, completed: !t.completed } : t
        ),
      };
      setSelectedList(updated);
      setLists(lists.map((l) => (l.id === updated.id ? updated : l)));
    } catch (error) {
      console.error('Failed to toggle task:', error);
    }
  };

  const handleDeleteTask = async (task: Task) => {
    if (!selectedList) return;
    try {
      await api.deleteTask(selectedList.id, task.id);
      const updated = {
        ...selectedList,
        tasks: selectedList.tasks.filter((t) => t.id !== task.id),
      };
      setSelectedList(updated);
      setLists(lists.map((l) => (l.id === updated.id ? updated : l)));
    } catch (error) {
      console.error('Failed to delete task:', error);
    }
  };

  const mainTasks = selectedList?.tasks.filter((t) => !t.parent_id) || [];

  return (
    <div className="task-list-app">
      <div className="task-list-sidebar">
        <div className="task-list-header">
          <h3>Lists</h3>
          <button onClick={handleNewList}>+</button>
        </div>
        <div className="task-list-lists">
          {lists.map((list) => (
            <div
              key={list.id}
              className={`task-list-item ${selectedList?.id === list.id ? 'active' : ''}`}
              onClick={() => setSelectedList(list)}
            >
              {list.name} ({list.tasks.filter((t) => !t.completed).length})
            </div>
          ))}
        </div>
      </div>

      <div className="task-list-main">
        {selectedList ? (
          <>
            <div className="task-list-title">
              <h2>{selectedList.name}</h2>
            </div>

            <div className="task-list-add">
              <input
                type="text"
                placeholder="Add new task..."
                value={newTaskTitle}
                onChange={(e) => setNewTaskTitle(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleAddTask()}
              />
              <button onClick={handleAddTask}>Add</button>
            </div>

            <div className="task-list-tasks">
              {mainTasks.length === 0 ? (
                <div className="task-list-empty">No tasks yet</div>
              ) : (
                mainTasks.map((task) => (
                  <div key={task.id} className="task-list-task">
                    <input
                      type="checkbox"
                      checked={task.completed}
                      onChange={() => handleToggleTask(task)}
                    />
                    <span className={task.completed ? 'task-completed' : ''}>
                      {task.title}
                    </span>
                    <button onClick={() => handleDeleteTask(task)}>×</button>
                  </div>
                ))
              )}
            </div>
          </>
        ) : (
          <div className="task-list-placeholder">
            <p>Select or create a task list</p>
            <button onClick={handleNewList}>Create New List</button>
          </div>
        )}
      </div>
    </div>
  );
}
