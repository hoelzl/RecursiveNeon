import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TaskListApp } from '../TaskListApp';
import { WebSocketProvider } from '../../../contexts/WebSocketContext';
import type { TaskList, Task } from '../../../types';

// Mock task lists
const mockTaskLists: TaskList[] = [
  {
    id: 'list-1',
    name: 'Work Tasks',
    tasks: [
      { id: 'task-1', title: 'Complete report', completed: false, parent_id: null },
      { id: 'task-2', title: 'Review PR', completed: true, parent_id: null },
    ],
    createdAt: '2024-01-01',
    updatedAt: '2024-01-01',
  },
  {
    id: 'list-2',
    name: 'Personal',
    tasks: [
      { id: 'task-3', title: 'Buy groceries', completed: false, parent_id: null },
    ],
    createdAt: '2024-01-02',
    updatedAt: '2024-01-02',
  },
];

// Mock WebSocket client implementing IWebSocketClient interface
const eventHandlers = new Map<string, Set<Function>>();

const mockWebSocketClient = {
  connect: vi.fn().mockResolvedValue(undefined),
  disconnect: vi.fn(),
  isConnected: vi.fn().mockReturnValue(true),
  
  on: vi.fn((event: string, handler: Function) => {
    if (!eventHandlers.has(event)) {
      eventHandlers.set(event, new Set());
    }
    eventHandlers.get(event)!.add(handler);
  }),
  off: vi.fn((event: string, handler: Function) => {
    eventHandlers.get(event)?.delete(handler);
  }),
  send: vi.fn((type: string, data: any = {}) => {
    // Simulate async response
    queueMicrotask(() => {
      const handlers = eventHandlers.get('app_response');
      if (handlers) {
        handlers.forEach(handler => {
          handler({
            type: 'app_response',
            data: getMockResponse(data.operation, data.payload),
          });
        });
      }
    });
  }),
} as any;

function getMockResponse(operation: string, payload: any): any {
  if (operation === 'tasks.lists') {
    return { lists: mockTaskLists };
  } else if (operation === 'tasks.list.create') {
    return {
      list: {
        id: 'list-3',
        name: payload.name || 'New List',
        tasks: [],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      },
    };
  } else if (operation === 'tasks.list.update') {
    const list = mockTaskLists.find((l) => l.id === payload.id);
    return {
      list: {
        ...list,
        name: payload.name,
        updatedAt: new Date().toISOString(),
      },
    };
  } else if (operation === 'tasks.list.delete') {
    return { success: true };
  } else if (operation === 'tasks.create') {
    return {
      task: {
        id: `task-${Date.now()}`,
        title: payload.title || 'New Task',
        completed: payload.completed || false,
        parent_id: null,
      },
    };
  } else if (operation === 'tasks.update') {
    return {
      task: {
        ...payload,
        updatedAt: new Date().toISOString(),
      },
    };
  } else if (operation === 'tasks.delete') {
    return { success: true };
  }
  return {};
}

// Helper to render with WebSocket context
const renderTaskListApp = () => {
  return render(
    <WebSocketProvider client={mockWebSocketClient}>
      <TaskListApp />
    </WebSocketProvider>
  );
};

// Helper to simulate API responses
const simulateApiResponse = (data: any) => {
  const messageHandler = mockWebSocketClient.addEventListener.mock.calls.find(
    (call: any[]) => call[0] === 'message'
  )?.[1];

  if (messageHandler) {
    messageHandler({ data: JSON.stringify(data) });
  }
};

describe('TaskListApp', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    eventHandlers.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Initialization', () => {
    it('should render loading state initially', () => {
      renderTaskListApp();
      // Component should be rendered
      expect(screen.getByRole('application', { hidden: true }) || document.body).toBeTruthy();
    });

    it('should load task lists on mount', async () => {
      renderTaskListApp();

      // Wait for getTaskLists API call
      await waitFor(() => {
        expect(mockWebSocketClient.send).toHaveBeenCalledWith(
          expect.objectContaining({
            type: 'app',
            data: expect.objectContaining({
              action: 'get_task_lists',
            }),
          })
        );
      });
    });

    it('should display task lists after loading', async () => {
      renderTaskListApp();

      // Simulate successful lists load
      await waitFor(() => {
        const calls = mockWebSocketClient.send.mock.calls;
        if (calls.length > 0) {
          simulateApiResponse({
            type: 'app_response',
            data: {
              action: 'get_task_lists',
              task_lists: mockTaskLists,
            },
          });
        }
      });

      await waitFor(() => {
        expect(screen.getByText(/Work Tasks/)).toBeInTheDocument();
        expect(screen.getByText(/Personal/)).toBeInTheDocument();
      });
    });

    it('should select first list by default', async () => {
      renderTaskListApp();

      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'get_task_lists',
          task_lists: mockTaskLists,
        },
      });

      await waitFor(() => {
        expect(screen.getByText('Complete report')).toBeInTheDocument();
        expect(screen.getByText('Review PR')).toBeInTheDocument();
      });
    });

    it('should show placeholder when no lists exist', async () => {
      renderTaskListApp();

      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'get_task_lists',
          task_lists: [],
        },
      });

      await waitFor(() => {
        expect(screen.getByText(/Select or create a task list/)).toBeInTheDocument();
      });
    });
  });

  describe('List Selection', () => {
    it('should display selected list tasks', async () => {
      const user = userEvent.setup();
      renderTaskListApp();

      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'get_task_lists',
          task_lists: mockTaskLists,
        },
      });

      await waitFor(() => {
        expect(screen.getByText('Complete report')).toBeInTheDocument();
      });
    });

    it('should switch lists when clicking on different list', async () => {
      const user = userEvent.setup();
      renderTaskListApp();

      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'get_task_lists',
          task_lists: mockTaskLists,
        },
      });

      await waitFor(() => {
        expect(screen.getByText(/Personal/)).toBeInTheDocument();
      });

      // Click on Personal list
      await user.click(screen.getByText(/Personal/));

      await waitFor(() => {
        expect(screen.getByText('Buy groceries')).toBeInTheDocument();
      });
    });

    it('should show task count in list item', async () => {
      renderTaskListApp();

      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'get_task_lists',
          task_lists: mockTaskLists,
        },
      });

      await waitFor(() => {
        // Work Tasks has 1 incomplete task (task-1)
        expect(screen.getByText(/Work Tasks \(1\)/)).toBeInTheDocument();
        // Personal has 1 incomplete task (task-3)
        expect(screen.getByText(/Personal \(1\)/)).toBeInTheDocument();
      });
    });
  });

  describe('List Management', () => {
    it('should create new list when clicking new button', async () => {
      const user = userEvent.setup();
      renderTaskListApp();

      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'get_task_lists',
          task_lists: mockTaskLists,
        },
      });

      await waitFor(() => {
        expect(screen.getByText(/Work Tasks/)).toBeInTheDocument();
      });

      // Click new list button
      const newButtons = screen.getAllByText('+');
      await user.click(newButtons[0]);

      // Dialog should appear
      await waitFor(() => {
        expect(screen.getByText('Create New List')).toBeInTheDocument();
      });
    });

    it('should add new list after creation', async () => {
      const user = userEvent.setup();
      renderTaskListApp();

      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'get_task_lists',
          task_lists: mockTaskLists,
        },
      });

      await waitFor(() => {
        expect(screen.getByText(/Work Tasks/)).toBeInTheDocument();
      });

      // Click new list button
      const newButtons = screen.getAllByText('+');
      await user.click(newButtons[0]);

      // Wait for dialog
      await waitFor(() => {
        expect(screen.getByText('Create New List')).toBeInTheDocument();
      });

      // Type new list name
      const input = screen.getByDisplayValue('New List');
      await user.clear(input);
      await user.type(input, 'Shopping List');

      // Confirm dialog
      const confirmButton = screen.getByText(/^OK$/i) || screen.getByText(/Confirm/i);
      await user.click(confirmButton);

      // Should call create_task_list API
      await waitFor(() => {
        const createCall = mockWebSocketClient.send.mock.calls.find(
          (call: any) => call[0]?.data?.action === 'create_task_list'
        );
        expect(createCall).toBeTruthy();
      });

      // Simulate successful creation
      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'create_task_list',
          task_list: {
            id: 'list-3',
            name: 'Shopping List',
            tasks: [],
            createdAt: '2024-01-03',
            updatedAt: '2024-01-03',
          },
        },
      });

      await waitFor(() => {
        expect(screen.getByText(/Shopping List/)).toBeInTheDocument();
      });
    });
  });

  describe('Task Management', () => {
    it('should add new task when clicking add button', async () => {
      const user = userEvent.setup();
      renderTaskListApp();

      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'get_task_lists',
          task_lists: mockTaskLists,
        },
      });

      await waitFor(() => {
        expect(screen.getByText('Complete report')).toBeInTheDocument();
      });

      // Type new task
      const input = screen.getByPlaceholderText(/Add new task/);
      await user.type(input, 'New urgent task');

      // Click add button
      const addButton = screen.getByText('Add');
      await user.click(addButton);

      // Should call create_task API
      await waitFor(() => {
        const createCall = mockWebSocketClient.send.mock.calls.find(
          (call: any) => call[0]?.data?.action === 'create_task'
        );
        expect(createCall).toBeTruthy();
      });
    });

    it('should add task when pressing Enter', async () => {
      const user = userEvent.setup();
      renderTaskListApp();

      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'get_task_lists',
          task_lists: mockTaskLists,
        },
      });

      await waitFor(() => {
        expect(screen.getByText('Complete report')).toBeInTheDocument();
      });

      // Type new task
      const input = screen.getByPlaceholderText(/Add new task/);
      await user.type(input, 'Press enter task{Enter}');

      // Should call create_task API
      await waitFor(() => {
        const createCall = mockWebSocketClient.send.mock.calls.find(
          (call: any) => call[0]?.data?.action === 'create_task'
        );
        expect(createCall).toBeTruthy();
      });
    });

    it('should clear input after adding task', async () => {
      const user = userEvent.setup();
      renderTaskListApp();

      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'get_task_lists',
          task_lists: mockTaskLists,
        },
      });

      await waitFor(() => {
        expect(screen.getByText('Complete report')).toBeInTheDocument();
      });

      // Type and add task
      const input = screen.getByPlaceholderText(/Add new task/) as HTMLInputElement;
      await user.type(input, 'Test task');

      const addButton = screen.getByText('Add');
      await user.click(addButton);

      // Simulate successful creation
      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'create_task',
          task: {
            id: 'task-new',
            title: 'Test task',
            completed: false,
            parent_id: null,
          },
        },
      });

      // Input should be cleared
      await waitFor(() => {
        expect(input.value).toBe('');
      });
    });

    it('should toggle task completion', async () => {
      const user = userEvent.setup();
      renderTaskListApp();

      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'get_task_lists',
          task_lists: mockTaskLists,
        },
      });

      await waitFor(() => {
        expect(screen.getByText('Complete report')).toBeInTheDocument();
      });

      // Find checkbox for incomplete task
      const checkboxes = screen.getAllByRole('checkbox');
      const incompleteCheckbox = checkboxes.find((cb) => !(cb as HTMLInputElement).checked);

      if (incompleteCheckbox) {
        await user.click(incompleteCheckbox);

        // Should call update_task API
        await waitFor(() => {
          const updateCall = mockWebSocketClient.send.mock.calls.find(
            (call: any) => call[0]?.data?.action === 'update_task'
          );
          expect(updateCall).toBeTruthy();
        });
      }
    });

    it('should delete task when clicking delete button', async () => {
      const user = userEvent.setup();
      renderTaskListApp();

      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'get_task_lists',
          task_lists: mockTaskLists,
        },
      });

      await waitFor(() => {
        expect(screen.getByText('Complete report')).toBeInTheDocument();
      });

      // Click delete button (×)
      const deleteButtons = screen.getAllByText('×');
      if (deleteButtons.length > 0) {
        await user.click(deleteButtons[0]);

        // Should call delete_task API
        await waitFor(() => {
          const deleteCall = mockWebSocketClient.send.mock.calls.find(
            (call: any) => call[0]?.data?.action === 'delete_task'
          );
          expect(deleteCall).toBeTruthy();
        });
      }
    });

    it('should show completed tasks with strikethrough', async () => {
      renderTaskListApp();

      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'get_task_lists',
          task_lists: mockTaskLists,
        },
      });

      await waitFor(() => {
        const completedTask = screen.getByText('Review PR');
        expect(completedTask).toHaveClass('task-completed');
      });
    });

    it('should show empty state when no tasks', async () => {
      renderTaskListApp();

      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'get_task_lists',
          task_lists: [
            {
              id: 'list-empty',
              name: 'Empty List',
              tasks: [],
              createdAt: '2024-01-01',
              updatedAt: '2024-01-01',
            },
          ],
        },
      });

      await waitFor(() => {
        expect(screen.getByText('No tasks yet')).toBeInTheDocument();
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle failed list loading', async () => {
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
      renderTaskListApp();

      // Simulate error response
      simulateApiResponse({
        type: 'error',
        data: {
          message: 'Failed to load task lists',
        },
      });

      await waitFor(() => {
        expect(consoleError).toHaveBeenCalled();
      });

      consoleError.mockRestore();
    });

    it('should handle failed task creation', async () => {
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
      const user = userEvent.setup();
      renderTaskListApp();

      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'get_task_lists',
          task_lists: mockTaskLists,
        },
      });

      await waitFor(() => {
        expect(screen.getByText('Complete report')).toBeInTheDocument();
      });

      // Try to add task
      const input = screen.getByPlaceholderText(/Add new task/);
      await user.type(input, 'Failed task');

      const addButton = screen.getByText('Add');
      await user.click(addButton);

      // Simulate error response
      simulateApiResponse({
        type: 'error',
        data: {
          message: 'Failed to create task',
        },
      });

      await waitFor(() => {
        expect(consoleError).toHaveBeenCalled();
      });

      consoleError.mockRestore();
    });

    it('should handle failed task toggle', async () => {
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
      const user = userEvent.setup();
      renderTaskListApp();

      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'get_task_lists',
          task_lists: mockTaskLists,
        },
      });

      await waitFor(() => {
        expect(screen.getByText('Complete report')).toBeInTheDocument();
      });

      // Toggle task
      const checkboxes = screen.getAllByRole('checkbox');
      if (checkboxes.length > 0) {
        await user.click(checkboxes[0]);

        // Simulate error response
        simulateApiResponse({
          type: 'error',
          data: {
            message: 'Failed to toggle task',
          },
        });

        await waitFor(() => {
          expect(consoleError).toHaveBeenCalled();
        });
      }

      consoleError.mockRestore();
    });

    it('should handle failed task deletion', async () => {
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
      const user = userEvent.setup();
      renderTaskListApp();

      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'get_task_lists',
          task_lists: mockTaskLists,
        },
      });

      await waitFor(() => {
        expect(screen.getByText('Complete report')).toBeInTheDocument();
      });

      // Delete task
      const deleteButtons = screen.getAllByText('×');
      if (deleteButtons.length > 0) {
        await user.click(deleteButtons[0]);

        // Simulate error response
        simulateApiResponse({
          type: 'error',
          data: {
            message: 'Failed to delete task',
          },
        });

        await waitFor(() => {
          expect(consoleError).toHaveBeenCalled();
        });
      }

      consoleError.mockRestore();
    });
  });
});
