/**
 * Task List App - Manage tasks and subtasks across multiple lists
 */
import React, { useState, useEffect } from 'react';
import { useWebSocket } from '../../contexts/WebSocketContext';
import { AppAPI } from '../../utils/appApi';
import { TaskList, Task } from '../../types';
import { Dialog } from '../Dialog';

type DialogType = 'newList' | 'editList' | 'editTask' | null;

export function TaskListApp() {
  const wsClient = useWebSocket();
  const api = new AppAPI(wsClient);

  const [lists, setLists] = useState<TaskList[]>([]);
  const [selectedList, setSelectedList] = useState<TaskList | null>(null);
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [dialog, setDialog] = useState<{
    type: DialogType;
    title: string;
    defaultValue?: string;
    listId?: string;
    taskId?: string;
  } | null>(null);
  const [contextMenu, setContextMenu] = useState<{
    x: number;
    y: number;
    type: 'list' | 'task';
    listId?: string;
    taskId?: string;
  } | null>(null);

  useEffect(() => {
    loadLists();
  }, []);

  useEffect(() => {
    const handleClickOutside = () => setContextMenu(null);
    if (contextMenu) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [contextMenu]);

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

  const handleNewList = () => {
    setDialog({ type: 'newList', title: 'Create New List', defaultValue: 'New List' });
  };

  const handleDialogConfirm = async (value?: string) => {
    if (!dialog || !value?.trim()) {
      setDialog(null);
      return;
    }

    try {
      if (dialog.type === 'newList') {
        const newList = await api.createTaskList(value);
        setLists([...lists, newList]);
        setSelectedList(newList);
      } else if (dialog.type === 'editList' && dialog.listId) {
        await api.updateTaskList(dialog.listId, value);
        const updated = lists.map((l) => (l.id === dialog.listId ? { ...l, name: value } : l));
        setLists(updated);
        if (selectedList?.id === dialog.listId) {
          setSelectedList({ ...selectedList, name: value });
        }
      } else if (dialog.type === 'editTask' && dialog.listId && dialog.taskId && selectedList) {
        await api.updateTask(dialog.listId, dialog.taskId, { title: value });
        const updatedTasks = selectedList.tasks.map((t) =>
          t.id === dialog.taskId ? { ...t, title: value } : t
        );
        const updatedList = { ...selectedList, tasks: updatedTasks };
        setSelectedList(updatedList);
        setLists(lists.map((l) => (l.id === dialog.listId ? updatedList : l)));
      }
    } catch (error) {
      console.error('Failed to process dialog:', error);
    }

    setDialog(null);
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

  const handleDeleteList = async (listId: string) => {
    try {
      await api.deleteTaskList(listId);
      const remaining = lists.filter((l) => l.id !== listId);
      setLists(remaining);

      if (selectedList?.id === listId) {
        setSelectedList(remaining.length > 0 ? remaining[0] : null);
      }

      setContextMenu(null);
    } catch (error) {
      console.error('Failed to delete task list:', error);
    }
  };

  const handleContextMenu = (
    e: React.MouseEvent,
    type: 'list' | 'task',
    listId?: string,
    taskId?: string
  ) => {
    e.preventDefault();
    e.stopPropagation();
    // Calculate position relative to the app container
    const appElement = (e.currentTarget as HTMLElement).closest('.task-list-app');
    if (appElement) {
      const rect = appElement.getBoundingClientRect();
      setContextMenu({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
        type,
        listId,
        taskId
      });
    }
  };

  const handleEditList = (listId: string) => {
    const list = lists.find((l) => l.id === listId);
    if (list) {
      setDialog({
        type: 'editList',
        title: 'Edit List Name',
        defaultValue: list.name,
        listId,
      });
    }
    setContextMenu(null);
  };

  const handleEditTask = (listId: string, taskId: string) => {
    const task = selectedList?.tasks.find((t) => t.id === taskId);
    if (task) {
      setDialog({
        type: 'editTask',
        title: 'Edit Task',
        defaultValue: task.title,
        listId,
        taskId,
      });
    }
    setContextMenu(null);
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
              onContextMenu={(e) => handleContextMenu(e, 'list', list.id)}
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
                  <div
                    key={task.id}
                    className="task-list-task"
                    onContextMenu={(e) => handleContextMenu(e, 'task', selectedList.id, task.id)}
                  >
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

      {dialog && (
        <Dialog
          title={dialog.title}
          defaultValue={dialog.defaultValue}
          onConfirm={handleDialogConfirm}
          onCancel={() => setDialog(null)}
        />
      )}

      {contextMenu && (
        <div
          className="context-menu"
          style={{ left: contextMenu.x, top: contextMenu.y }}
        >
          {contextMenu.type === 'list' && contextMenu.listId && (
            <>
              <div
                className="context-menu-item"
                onClick={() => handleEditList(contextMenu.listId!)}
              >
                Rename List
              </div>
              <div
                className="context-menu-item"
                onClick={() => handleDeleteList(contextMenu.listId!)}
              >
                Delete List
              </div>
            </>
          )}
          {contextMenu.type === 'task' && contextMenu.listId && contextMenu.taskId && (
            <>
              <div
                className="context-menu-item"
                onClick={() => handleEditTask(contextMenu.listId!, contextMenu.taskId!)}
              >
                Edit Task
              </div>
              <div
                className="context-menu-item"
                onClick={() => {
                  const task = selectedList?.tasks.find((t) => t.id === contextMenu.taskId);
                  if (task) handleDeleteTask(task);
                  setContextMenu(null);
                }}
              >
                Delete Task
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
