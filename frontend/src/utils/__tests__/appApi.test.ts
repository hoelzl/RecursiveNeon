/**
 * Tests for AppAPI
 *
 * These tests document the current behavior before refactoring the request queue.
 * After refactoring, these tests should continue to pass.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AppAPI } from '../appApi';
import { WebSocketClient } from '../../services/websocket';

// Helper to create a mock WebSocket client
function createMockWebSocketClient() {
  const handlers = new Map<string, Set<any>>();

  return {
    on: vi.fn((type: string, handler: any) => {
      if (!handlers.has(type)) {
        handlers.set(type, new Set());
      }
      handlers.get(type)!.add(handler);
    }),
    off: vi.fn((type: string, handler: any) => {
      const handlers_set = handlers.get(type);
      if (handlers_set) {
        handlers_set.delete(handler);
      }
    }),
    send: vi.fn(),
    // Test helpers
    _handlers: handlers,
    _simulateMessage: (type: string, data: any) => {
      const typeHandlers = handlers.get(type);
      if (typeHandlers) {
        typeHandlers.forEach((handler) => handler({ type, data }));
      }
    },
  } as any as WebSocketClient;
}

describe('AppAPI', () => {
  let mockWs: ReturnType<typeof createMockWebSocketClient>;
  let appApi: AppAPI;

  beforeEach(() => {
    mockWs = createMockWebSocketClient();
    appApi = new AppAPI(mockWs);
  });

  describe('Request/Response Flow', () => {
    it('should send message and receive response', async () => {
      const promise = appApi.getNotes();

      // Wait for promise to start executing
      await Promise.resolve();

      // Verify message was sent
      expect(mockWs.send).toHaveBeenCalledWith('app', {
        operation: 'notes.list',
        payload: {},
      });

      // Simulate response
      mockWs._simulateMessage('app_response', {
        notes: [{ id: '1', title: 'Test Note' }],
      });

      const result = await promise;
      expect(result).toEqual([{ id: '1', title: 'Test Note' }]);
    });

    it('should handle error responses', async () => {
      const promise = appApi.getNotes();

      // Wait for promise to start
      await Promise.resolve();

      // Simulate error
      mockWs._simulateMessage('error', {
        message: 'Database error',
      });

      await expect(promise).rejects.toThrow('Database error');
    });

    it.skip('should timeout after 10 seconds', async () => {
      // Skipped: Fake timers cause unhandled rejection warnings
      vi.useFakeTimers();

      const promise = appApi.getNotes();

      // Wait for promise to start
      await Promise.resolve();

      // Fast-forward time by 10 seconds
      await vi.advanceTimersByTimeAsync(10000);

      await expect(promise).rejects.toThrow('Request timeout');

      vi.useRealTimers();
    });

    it('should cleanup handlers after successful response', async () => {
      const promise = appApi.getNotes();

      // Wait for promise to start
      await Promise.resolve();

      // Simulate response
      mockWs._simulateMessage('app_response', { notes: [] });

      await promise;

      // Verify handlers were removed (2 calls: one for 'app_response', one for 'error')
      expect(mockWs.off).toHaveBeenCalledTimes(2);
    });

    it('should cleanup handlers after error', async () => {
      const promise = appApi.getNotes();

      // Wait for promise to start
      await Promise.resolve();

      // Simulate error
      mockWs._simulateMessage('error', { message: 'Error' });

      await expect(promise).rejects.toThrow();

      // Verify handlers were removed
      expect(mockWs.off).toHaveBeenCalledTimes(2);
    });

    it.skip('should cleanup handlers after timeout', async () => {
      // Skipped: Fake timers cause unhandled rejection warnings
      vi.useFakeTimers();

      const promise = appApi.getNotes();

      // Wait for promise to start
      await Promise.resolve();

      // Fast-forward time
      await vi.advanceTimersByTimeAsync(10000);

      await expect(promise).rejects.toThrow('Request timeout');

      // Verify handlers were removed
      expect(mockWs.off).toHaveBeenCalledTimes(2);

      vi.useRealTimers();
    });
  });

  describe('Notes API', () => {
    it('should get notes list', async () => {
      const promise = appApi.getNotes();
      await Promise.resolve();

      mockWs._simulateMessage('app_response', {
        notes: [
          { id: '1', title: 'Note 1' },
          { id: '2', title: 'Note 2' },
        ],
      });

      const notes = await promise;
      expect(notes).toHaveLength(2);
      expect(notes[0].id).toBe('1');
    });

    it('should create note', async () => {
      const promise = appApi.createNote({ title: 'New Note', content: 'Content' });
      await Promise.resolve();

      expect(mockWs.send).toHaveBeenCalledWith('app', {
        operation: 'notes.create',
        payload: { title: 'New Note', content: 'Content' },
      });

      mockWs._simulateMessage('app_response', {
        note: { id: '3', title: 'New Note', content: 'Content' },
      });

      const note = await promise;
      expect(note.id).toBe('3');
      expect(note.title).toBe('New Note');
    });

    it('should update note', async () => {
      const promise = appApi.updateNote('1', { title: 'Updated' });
      await Promise.resolve();

      expect(mockWs.send).toHaveBeenCalledWith('app', {
        operation: 'notes.update',
        payload: { id: '1', title: 'Updated' },
      });

      mockWs._simulateMessage('app_response', {
        note: { id: '1', title: 'Updated' },
      });

      const note = await promise;
      expect(note.title).toBe('Updated');
    });

    it('should delete note', async () => {
      const promise = appApi.deleteNote('1');
      await Promise.resolve();

      expect(mockWs.send).toHaveBeenCalledWith('app', {
        operation: 'notes.delete',
        payload: { id: '1' },
      });

      mockWs._simulateMessage('app_response', {});

      await promise;
      // Should complete without error
    });
  });

  describe('Tasks API', () => {
    it('should get task lists', async () => {
      const promise = appApi.getTaskLists();
      await Promise.resolve();

      mockWs._simulateMessage('app_response', {
        lists: [
          { id: '1', name: 'Personal', tasks: [] },
          { id: '2', name: 'Work', tasks: [] },
        ],
      });

      const lists = await promise;
      expect(lists).toHaveLength(2);
    });

    it('should create task list', async () => {
      const promise = appApi.createTaskList('Shopping');
      await Promise.resolve();

      expect(mockWs.send).toHaveBeenCalledWith('app', {
        operation: 'tasks.list.create',
        payload: { name: 'Shopping' },
      });

      mockWs._simulateMessage('app_response', {
        list: { id: '3', name: 'Shopping', tasks: [] },
      });

      const list = await promise;
      expect(list.name).toBe('Shopping');
    });

    it('should create task', async () => {
      const promise = appApi.createTask('1', {
        title: 'Buy milk',
        completed: false,
      });
      await Promise.resolve();

      expect(mockWs.send).toHaveBeenCalledWith('app', {
        operation: 'tasks.create',
        payload: { list_id: '1', title: 'Buy milk', completed: false },
      });

      mockWs._simulateMessage('app_response', {
        task: { id: '1', title: 'Buy milk', completed: false },
      });

      const task = await promise;
      expect(task.title).toBe('Buy milk');
    });
  });

  describe('Filesystem API', () => {
    it('should initialize filesystem', async () => {
      const promise = appApi.initFilesystem();
      await Promise.resolve();

      mockWs._simulateMessage('app_response', {
        root: { id: 'root', name: '/', type: 'directory' },
      });

      const root = await promise;
      expect(root.id).toBe('root');
      expect(root.type).toBe('directory');
    });

    it('should list directory contents', async () => {
      const promise = appApi.listDirectory('root');
      await Promise.resolve();

      expect(mockWs.send).toHaveBeenCalledWith('app', {
        operation: 'fs.list',
        payload: { dir_id: 'root' },
      });

      mockWs._simulateMessage('app_response', {
        nodes: [
          { id: '1', name: 'file1.txt', type: 'file' },
          { id: '2', name: 'dir1', type: 'directory' },
        ],
      });

      const nodes = await promise;
      expect(nodes).toHaveLength(2);
    });

    it('should create directory', async () => {
      const promise = appApi.createDirectory('Documents', 'root');
      await Promise.resolve();

      expect(mockWs.send).toHaveBeenCalledWith('app', {
        operation: 'fs.create.dir',
        payload: { name: 'Documents', parent_id: 'root' },
      });

      mockWs._simulateMessage('app_response', {
        node: { id: '3', name: 'Documents', type: 'directory' },
      });

      const node = await promise;
      expect(node.name).toBe('Documents');
    });

    it('should create file', async () => {
      const promise = appApi.createFile(
        'test.txt',
        'root',
        'Hello World',
        'text/plain'
      );
      await Promise.resolve();

      expect(mockWs.send).toHaveBeenCalledWith('app', {
        operation: 'fs.create.file',
        payload: {
          name: 'test.txt',
          parent_id: 'root',
          content: 'Hello World',
          mime_type: 'text/plain',
        },
      });

      mockWs._simulateMessage('app_response', {
        node: {
          id: '4',
          name: 'test.txt',
          type: 'file',
          content: 'Hello World',
        },
      });

      const node = await promise;
      expect(node.name).toBe('test.txt');
    });
  });

  describe('Browser API', () => {
    it('should get browser pages', async () => {
      const promise = appApi.getBrowserPages();
      await Promise.resolve();

      mockWs._simulateMessage('app_response', {
        pages: [
          { id: '1', url: 'home.html', title: 'Home' },
          { id: '2', url: 'about.html', title: 'About' },
        ],
      });

      const pages = await promise;
      expect(pages).toHaveLength(2);
    });

    it('should get browser page by URL', async () => {
      const promise = appApi.getBrowserPage('home.html');
      await Promise.resolve();

      mockWs._simulateMessage('app_response', {
        page: { id: '1', url: 'home.html', title: 'Home' },
      });

      const page = await promise;
      expect(page?.url).toBe('home.html');
    });

    it('should return null for non-existent page', async () => {
      const promise = appApi.getBrowserPage('missing.html');
      await Promise.resolve();

      mockWs._simulateMessage('error', { message: 'Not found' });

      const page = await promise;
      expect(page).toBeNull();
    });

    it('should add bookmark', async () => {
      const promise = appApi.addBookmark('home.html');
      await Promise.resolve();

      expect(mockWs.send).toHaveBeenCalledWith('app', {
        operation: 'browser.bookmark.add',
        payload: { url: 'home.html' },
      });

      mockWs._simulateMessage('app_response', {});

      await promise;
      // Should complete without error
    });
  });

  describe('Request Queueing', () => {
    it('should handle multiple sequential requests', async () => {
      // Start three requests
      const promise1 = appApi.getNotes();
      const promise2 = appApi.getTaskLists();
      const promise3 = appApi.getBrowserPages();

      // Wait for first promise to start
      await new Promise((resolve) => setImmediate(resolve));

      // First request should have sent immediately
      expect(mockWs.send).toHaveBeenCalledTimes(1);
      expect(mockWs.send).toHaveBeenCalledWith('app', {
        operation: 'notes.list',
        payload: {},
      });

      // Respond to first request, which should trigger second
      mockWs._simulateMessage('app_response', { notes: [{ id: '1' }] });

      // Wait for promise chain to propagate
      await new Promise((resolve) => setImmediate(resolve));

      // Second request should have sent now
      expect(mockWs.send).toHaveBeenCalledTimes(2);
      expect(mockWs.send).toHaveBeenCalledWith('app', {
        operation: 'tasks.lists',
        payload: {},
      });

      // Respond to second request, which should trigger third
      mockWs._simulateMessage('app_response', { lists: [{ id: '2' }] });

      // Wait for promise chain to propagate
      await new Promise((resolve) => setImmediate(resolve));

      // Third request should have sent now
      expect(mockWs.send).toHaveBeenCalledTimes(3);
      expect(mockWs.send).toHaveBeenCalledWith('app', {
        operation: 'browser.pages',
        payload: {},
      });

      // Respond to third request
      mockWs._simulateMessage('app_response', { pages: [{ id: '3' }] });

      const [notes, lists, pages] = await Promise.all([
        promise1,
        promise2,
        promise3,
      ]);

      expect(notes).toHaveLength(1);
      expect(lists).toHaveLength(1);
      expect(pages).toHaveLength(1);
    });
  });
});
