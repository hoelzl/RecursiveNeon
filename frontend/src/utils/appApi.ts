/**
 * API utilities for desktop apps
 * Provides helpers for communicating with backend app services
 */

import { WebSocketClient } from '../services/websocket';
import { Note, Task, TaskList, FileNode, BrowserPage } from '../types';

export class AppAPI {
  private requestQueue: Promise<any> = Promise.resolve();

  constructor(private ws: WebSocketClient) {}

  private async send(operation: string, payload: any = {}): Promise<any> {
    // Queue requests to prevent race conditions with WebSocket event handlers
    // Each request waits for the previous one to complete
    const request = async () => {
      return new Promise((resolve, reject) => {
        const handleResponse = (msg: any) => {
          if (msg.type === 'app_response') {
            this.ws.off('app_response', handleResponse);
            this.ws.off('error', handleResponse);
            resolve(msg.data);
          } else if (msg.type === 'error') {
            this.ws.off('app_response', handleResponse);
            this.ws.off('error', handleResponse);
            reject(new Error(msg.data.message));
          }
        };

        this.ws.on('app_response', handleResponse);
        this.ws.on('error', handleResponse);

        this.ws.send('app', { operation, payload });

        // Timeout after 10 seconds
        setTimeout(() => {
          this.ws.off('app_response', handleResponse);
          this.ws.off('error', handleResponse);
          reject(new Error('Request timeout'));
        }, 10000);
      });
    };

    // Chain this request after the previous one
    this.requestQueue = this.requestQueue.then(request, request);
    return this.requestQueue;
  }

  // Notes API
  async getNotes(): Promise<Note[]> {
    const data = await this.send('notes.list');
    return data.notes || [];
  }

  async createNote(note: Partial<Note>): Promise<Note> {
    const data = await this.send('notes.create', note);
    return data.note;
  }

  async updateNote(id: string, updates: Partial<Note>): Promise<Note> {
    const data = await this.send('notes.update', { id, ...updates });
    return data.note;
  }

  async deleteNote(id: string): Promise<void> {
    await this.send('notes.delete', { id });
  }

  // Tasks API
  async getTaskLists(): Promise<TaskList[]> {
    const data = await this.send('tasks.lists');
    return data.lists || [];
  }

  async createTaskList(name: string): Promise<TaskList> {
    const data = await this.send('tasks.list.create', { name });
    return data.list;
  }

  async updateTaskList(id: string, name: string): Promise<TaskList> {
    const data = await this.send('tasks.list.update', { id, name });
    return data.list;
  }

  async deleteTaskList(id: string): Promise<void> {
    await this.send('tasks.list.delete', { id });
  }

  async createTask(listId: string, task: Partial<Task>): Promise<Task> {
    const data = await this.send('tasks.create', { list_id: listId, ...task });
    return data.task;
  }

  async updateTask(listId: string, taskId: string, updates: Partial<Task>): Promise<Task> {
    const data = await this.send('tasks.update', { list_id: listId, id: taskId, ...updates });
    return data.task;
  }

  async deleteTask(listId: string, taskId: string): Promise<void> {
    await this.send('tasks.delete', { list_id: listId, id: taskId });
  }

  // Filesystem API
  async initFilesystem(): Promise<FileNode> {
    const data = await this.send('fs.init');
    return data.root;
  }

  async listDirectory(dirId: string): Promise<FileNode[]> {
    console.log('[AppAPI] Calling listDirectory with dirId:', dirId);
    const data = await this.send('fs.list', { dir_id: dirId });
    console.log('[AppAPI] listDirectory response data:', data);
    console.log('[AppAPI] listDirectory nodes:', data.nodes);
    return data.nodes || [];
  }

  async getFile(id: string): Promise<FileNode> {
    const data = await this.send('fs.get', { id });
    return data.node;
  }

  async createDirectory(name: string, parentId: string): Promise<FileNode> {
    const data = await this.send('fs.create.dir', { name, parent_id: parentId });
    return data.node;
  }

  async createFile(name: string, parentId: string, content: string, mimeType: string): Promise<FileNode> {
    const data = await this.send('fs.create.file', {
      name,
      parent_id: parentId,
      content,
      mime_type: mimeType,
    });
    return data.node;
  }

  async updateFile(id: string, updates: Partial<FileNode>): Promise<FileNode> {
    const data = await this.send('fs.update', { id, ...updates });
    return data.node;
  }

  async deleteFile(id: string): Promise<void> {
    await this.send('fs.delete', { id });
  }

  async copyFile(id: string, targetParentId: string, newName?: string): Promise<FileNode> {
    const data = await this.send('fs.copy', {
      id,
      target_parent_id: targetParentId,
      new_name: newName,
    });
    return data.node;
  }

  async moveFile(id: string, targetParentId: string): Promise<FileNode> {
    const data = await this.send('fs.move', { id, target_parent_id: targetParentId });
    return data.node;
  }

  // Browser API
  async getBrowserPages(): Promise<BrowserPage[]> {
    const data = await this.send('browser.pages');
    return data.pages || [];
  }

  async getBrowserPage(url: string): Promise<BrowserPage | null> {
    try {
      const data = await this.send('browser.page.get', { url });
      return data.page || null;
    } catch {
      return null;
    }
  }

  async createBrowserPage(page: Partial<BrowserPage>): Promise<BrowserPage> {
    const data = await this.send('browser.page.create', page);
    return data.page;
  }

  async getBookmarks(): Promise<string[]> {
    const data = await this.send('browser.bookmarks');
    return data.bookmarks || [];
  }

  async addBookmark(url: string): Promise<void> {
    await this.send('browser.bookmark.add', { url });
  }

  async removeBookmark(url: string): Promise<void> {
    await this.send('browser.bookmark.remove', { url });
  }
}
