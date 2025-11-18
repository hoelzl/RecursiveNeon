import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FileBrowserApp } from '../FileBrowserApp';
import { WebSocketProvider } from '../../../contexts/WebSocketContext';
import { GameStoreContext } from '../../../contexts/GameStoreContext';
import { useGameStore } from '../../../stores/gameStore';
import type { FileNode } from '../../../types';

// Mock game store
const mockOpenWindow = vi.fn();
const mockGameStore = {
  ...useGameStore.getState(),
  openWindow: mockOpenWindow,
};

// Mock filesystem data
const mockRootNode: FileNode = {
  id: 'root-id',
  name: 'home',
  type: 'directory',
  parent_id: null,
  mime_type: null,
  content: null,
};

const mockFiles: FileNode[] = [
  {
    id: 'file-1',
    name: 'readme.txt',
    type: 'file',
    parent_id: 'root-id',
    mime_type: 'text/plain',
    content: 'This is a readme file',
  },
  {
    id: 'dir-1',
    name: 'documents',
    type: 'directory',
    parent_id: 'root-id',
    mime_type: null,
    content: null,
  },
  {
    id: 'file-2',
    name: 'image.png',
    type: 'file',
    parent_id: 'root-id',
    mime_type: 'image/png',
    content: null,
  },
];

// Mock WebSocket client with event handling
const eventHandlers = new Map<string, Set<Function>>();

const mockWebSocketClient = {
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  sendMessage: vi.fn(),
  readyState: 1,
  on: vi.fn((event: string, handler: Function) => {
    if (!eventHandlers.has(event)) {
      eventHandlers.set(event, new Set());
    }
    eventHandlers.get(event)!.add(handler);
  }),
  off: vi.fn((event: string, handler: Function) => {
    eventHandlers.get(event)?.delete(handler);
  }),
  send: vi.fn((type: string, data: any) => {
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
  if (operation === 'init_filesystem') {
    return { root: mockRootNode };
  } else if (operation === 'list_directory') {
    return { nodes: mockFiles };
  } else if (operation === 'create_directory' || operation === 'create_file') {
    return {
      node: {
        id: `new-${Date.now()}`,
        name: payload.name || 'New Item',
        type: operation === 'create_directory' ? 'directory' : 'file',
        parent_id: payload.parent_id || 'root-id',
        mime_type: payload.mime_type || null,
        content: payload.content || null,
      },
    };
  } else if (operation === 'copy_file' || operation === 'move_file' || operation === 'update_file' || operation === 'delete_file') {
    return { success: true };
  }
  return {};
}

// Helper to render with contexts
const renderFileBrowserApp = () => {
  return render(
    <WebSocketProvider client={mockWebSocketClient}>
      <GameStoreContext.Provider value={mockGameStore as any}>
        <FileBrowserApp />
      </GameStoreContext.Provider>
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

describe('FileBrowserApp', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    eventHandlers.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Initialization', () => {
    it('should show loading state initially', () => {
      renderFileBrowserApp();
      expect(screen.getByText('Loading...')).toBeInTheDocument();
    });

    it('should initialize filesystem on mount', async () => {
      renderFileBrowserApp();

      // Wait for initFilesystem API call
      await waitFor(() => {
        expect(mockWebSocketClient.sendMessage).toHaveBeenCalledWith(
          expect.objectContaining({
            type: 'app',
            data: expect.objectContaining({
              action: 'init_filesystem',
            }),
          })
        );
      });
    });

    it('should load root directory after initialization', async () => {
      renderFileBrowserApp();

      // Simulate successful filesystem init
      await waitFor(() => {
        const calls = mockWebSocketClient.sendMessage.mock.calls;
        if (calls.length > 0) {
          simulateApiResponse({
            type: 'app_response',
            data: {
              action: 'init_filesystem',
              root: mockRootNode,
            },
          });
        }
      });

      // Should call list_directory for root
      await waitFor(() => {
        const listCall = mockWebSocketClient.sendMessage.mock.calls.find(
          (call: any) => call[0]?.data?.action === 'list_directory'
        );
        expect(listCall).toBeTruthy();
      });
    });

    it('should display files after loading', async () => {
      renderFileBrowserApp();

      // Init filesystem
      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'init_filesystem',
          root: mockRootNode,
        },
      });

      // Wait for list_directory call
      await waitFor(() => {
        const listCall = mockWebSocketClient.sendMessage.mock.calls.find(
          (call: any) => call[0]?.data?.action === 'list_directory'
        );
        if (listCall) {
          simulateApiResponse({
            type: 'app_response',
            data: {
              action: 'list_directory',
              nodes: mockFiles,
            },
          });
        }
      });

      await waitFor(() => {
        expect(screen.getByText('readme.txt')).toBeInTheDocument();
        expect(screen.getByText('documents')).toBeInTheDocument();
        expect(screen.getByText('image.png')).toBeInTheDocument();
      });
    });

    it('should show empty state when directory is empty', async () => {
      renderFileBrowserApp();

      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'init_filesystem',
          root: mockRootNode,
        },
      });

      await waitFor(() => {
        const listCall = mockWebSocketClient.sendMessage.mock.calls.find(
          (call: any) => call[0]?.data?.action === 'list_directory'
        );
        if (listCall) {
          simulateApiResponse({
            type: 'app_response',
            data: {
              action: 'list_directory',
              nodes: [],
            },
          });
        }
      });

      await waitFor(() => {
        expect(screen.getByText('This folder is empty')).toBeInTheDocument();
      });
    });
  });

  describe('Navigation', () => {
    beforeEach(async () => {
      renderFileBrowserApp();
      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'init_filesystem',
          root: mockRootNode,
        },
      });

      await waitFor(() => {
        const listCall = mockWebSocketClient.sendMessage.mock.calls.find(
          (call: any) => call[0]?.data?.action === 'list_directory'
        );
        if (listCall) {
          simulateApiResponse({
            type: 'app_response',
            data: {
              action: 'list_directory',
              nodes: mockFiles,
            },
          });
        }
      });
    });

    it('should open directory on double click', async () => {
      const user = userEvent.setup();

      await waitFor(() => {
        expect(screen.getByText('documents')).toBeInTheDocument();
      });

      // Double-click directory
      const dirElement = screen.getByText('documents');
      await user.dblClick(dirElement);

      // Should call list_directory for the directory
      await waitFor(() => {
        const listCalls = mockWebSocketClient.sendMessage.mock.calls.filter(
          (call: any) => call[0]?.data?.action === 'list_directory'
        );
        // Should have at least 2 calls: initial root + opened directory
        expect(listCalls.length).toBeGreaterThan(1);
      });
    });

    it('should update path when navigating into directory', async () => {
      const user = userEvent.setup();

      await waitFor(() => {
        expect(screen.getByText('documents')).toBeInTheDocument();
      });

      await user.dblClick(screen.getByText('documents'));

      // Path should update (check for breadcrumb)
      await waitFor(() => {
        const pathElement = document.querySelector('.file-browser-path');
        expect(pathElement?.textContent).toContain('documents');
      });
    });

    it('should navigate back when clicking up button', async () => {
      const user = userEvent.setup();

      await waitFor(() => {
        expect(screen.getByText('documents')).toBeInTheDocument();
      });

      // Navigate into directory
      await user.dblClick(screen.getByText('documents'));

      await waitFor(() => {
        const pathElement = document.querySelector('.file-browser-path');
        expect(pathElement?.textContent).toContain('documents');
      });

      // Click back button
      const upButton = screen.getByText(/↑ Up/);
      await user.click(upButton);

      // Should be back at root
      await waitFor(() => {
        const pathElement = document.querySelector('.file-browser-path');
        expect(pathElement?.textContent).not.toContain('documents');
      });
    });
  });

  describe('File Operations', () => {
    beforeEach(async () => {
      renderFileBrowserApp();
      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'init_filesystem',
          root: mockRootNode,
        },
      });

      await waitFor(() => {
        const listCall = mockWebSocketClient.sendMessage.mock.calls.find(
          (call: any) => call[0]?.data?.action === 'list_directory'
        );
        if (listCall) {
          simulateApiResponse({
            type: 'app_response',
            data: {
              action: 'list_directory',
              nodes: mockFiles,
            },
          });
        }
      });
    });

    it('should create new folder when clicking new folder button', async () => {
      const user = userEvent.setup();

      await waitFor(() => {
        expect(screen.getByText('readme.txt')).toBeInTheDocument();
      });

      // Click new folder button
      const newFolderButton = screen.getByText('+ New Folder');
      await user.click(newFolderButton);

      // Dialog should appear
      await waitFor(() => {
        expect(screen.getByText('Create New Folder')).toBeInTheDocument();
      });
    });

    it('should create new file when clicking new file button', async () => {
      const user = userEvent.setup();

      await waitFor(() => {
        expect(screen.getByText('readme.txt')).toBeInTheDocument();
      });

      // Click new file button
      const newFileButton = screen.getByText('+ New File');
      await user.click(newFileButton);

      // Dialog should appear
      await waitFor(() => {
        expect(screen.getByText('Create New File')).toBeInTheDocument();
      });
    });

    it('should select file on single click', async () => {
      const user = userEvent.setup();

      await waitFor(() => {
        expect(screen.getByText('readme.txt')).toBeInTheDocument();
      });

      // Click file
      const fileElement = screen.getByText('readme.txt');
      await user.click(fileElement);

      // File should be selected (check for selected class)
      await waitFor(() => {
        const parentElement = fileElement.closest('.file-browser-item');
        expect(parentElement).toHaveClass('selected');
      });
    });
  });

  describe('File Opening', () => {
    beforeEach(async () => {
      renderFileBrowserApp();
      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'init_filesystem',
          root: mockRootNode,
        },
      });

      await waitFor(() => {
        const listCall = mockWebSocketClient.sendMessage.mock.calls.find(
          (call: any) => call[0]?.data?.action === 'list_directory'
        );
        if (listCall) {
          simulateApiResponse({
            type: 'app_response',
            data: {
              action: 'list_directory',
              nodes: mockFiles,
            },
          });
        }
      });
    });

    it('should open text file in text editor on double click', async () => {
      const user = userEvent.setup();

      await waitFor(() => {
        expect(screen.getByText('readme.txt')).toBeInTheDocument();
      });

      // Double-click text file
      const fileElement = screen.getByText('readme.txt');
      await user.dblClick(fileElement);

      // Should call openWindow
      await waitFor(() => {
        expect(mockOpenWindow).toHaveBeenCalled();
        const call = mockOpenWindow.mock.calls[0][0];
        expect(call.type).toBe('text-editor');
        expect(call.title).toContain('readme.txt');
      });
    });

    it('should open image file in image viewer on double click', async () => {
      const user = userEvent.setup();

      await waitFor(() => {
        expect(screen.getByText('image.png')).toBeInTheDocument();
      });

      // Double-click image file
      const fileElement = screen.getByText('image.png');
      await user.dblClick(fileElement);

      // Should call openWindow
      await waitFor(() => {
        expect(mockOpenWindow).toHaveBeenCalled();
        const call = mockOpenWindow.mock.calls[0][0];
        expect(call.type).toBe('image-viewer');
        expect(call.title).toContain('image.png');
      });
    });
  });

  describe('Context Menu', () => {
    beforeEach(async () => {
      renderFileBrowserApp();
      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'init_filesystem',
          root: mockRootNode,
        },
      });

      await waitFor(() => {
        const listCall = mockWebSocketClient.sendMessage.mock.calls.find(
          (call: any) => call[0]?.data?.action === 'list_directory'
        );
        if (listCall) {
          simulateApiResponse({
            type: 'app_response',
            data: {
              action: 'list_directory',
              nodes: mockFiles,
            },
          });
        }
      });
    });

    it('should show context menu on right-click file', async () => {
      await waitFor(() => {
        expect(screen.getByText('readme.txt')).toBeInTheDocument();
      });

      // Right-click file
      const fileElement = screen.getByText('readme.txt');
      fireEvent.contextMenu(fileElement);

      // Context menu should appear
      await waitFor(() => {
        expect(screen.getByText(/Copy/)).toBeInTheDocument();
        expect(screen.getByText(/Cut/)).toBeInTheDocument();
        expect(screen.getByText(/Rename/)).toBeInTheDocument();
        expect(screen.getByText(/Delete/)).toBeInTheDocument();
      });
    });

    it('should show context menu on right-click background', async () => {
      await waitFor(() => {
        expect(screen.getByText('readme.txt')).toBeInTheDocument();
      });

      // Right-click background
      const contentArea = document.querySelector('.file-browser-content');
      if (contentArea) {
        fireEvent.contextMenu(contentArea);

        // Context menu should appear
        await waitFor(() => {
          expect(screen.getByText(/New File/)).toBeInTheDocument();
          expect(screen.getByText(/New Folder/)).toBeInTheDocument();
        });
      }
    });
  });

  describe('Copy/Cut/Paste Operations', () => {
    beforeEach(async () => {
      renderFileBrowserApp();
      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'init_filesystem',
          root: mockRootNode,
        },
      });

      await waitFor(() => {
        const listCall = mockWebSocketClient.sendMessage.mock.calls.find(
          (call: any) => call[0]?.data?.action === 'list_directory'
        );
        if (listCall) {
          simulateApiResponse({
            type: 'app_response',
            data: {
              action: 'list_directory',
              nodes: mockFiles,
            },
          });
        }
      });
    });

    it('should copy file via context menu', async () => {
      const user = userEvent.setup();

      await waitFor(() => {
        expect(screen.getByText('readme.txt')).toBeInTheDocument();
      });

      // Right-click file
      const fileElement = screen.getByText('readme.txt');
      fireEvent.contextMenu(fileElement);

      // Click copy
      await waitFor(() => {
        const copyButton = screen.getByText(/📄 Copy/);
        return user.click(copyButton);
      });

      // Paste button should appear in toolbar
      await waitFor(() => {
        expect(screen.getByText(/📋 Paste/)).toBeInTheDocument();
      });
    });

    it('should cut file via context menu', async () => {
      const user = userEvent.setup();

      await waitFor(() => {
        expect(screen.getByText('readme.txt')).toBeInTheDocument();
      });

      // Right-click file
      const fileElement = screen.getByText('readme.txt');
      fireEvent.contextMenu(fileElement);

      // Click cut
      await waitFor(() => {
        const cutButton = screen.getByText(/✂️ Cut/);
        return user.click(cutButton);
      });

      // Paste button should appear in toolbar
      await waitFor(() => {
        const pasteButton = screen.getByText(/📋 Paste/);
        expect(pasteButton.textContent).toContain('Move');
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle failed filesystem initialization', async () => {
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
      renderFileBrowserApp();

      // Simulate error response
      simulateApiResponse({
        type: 'error',
        data: {
          message: 'Failed to initialize filesystem',
        },
      });

      await waitFor(() => {
        expect(consoleError).toHaveBeenCalled();
      });

      consoleError.mockRestore();
    });

    it('should handle failed directory listing', async () => {
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
      renderFileBrowserApp();

      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'init_filesystem',
          root: mockRootNode,
        },
      });

      await waitFor(() => {
        const listCall = mockWebSocketClient.sendMessage.mock.calls.find(
          (call: any) => call[0]?.data?.action === 'list_directory'
        );
        if (listCall) {
          simulateApiResponse({
            type: 'error',
            data: {
              message: 'Failed to list directory',
            },
          });
        }
      });

      await waitFor(() => {
        expect(consoleError).toHaveBeenCalled();
      });

      consoleError.mockRestore();
    });
  });
});
