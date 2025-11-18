/**
 * Tests for App component
 *
 * These tests document the current behavior of App.tsx before refactoring.
 * After refactoring, these tests should continue to pass.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import App from './App';
import { WebSocketProvider } from './contexts/WebSocketContext';
import { GameStoreProvider } from './contexts/GameStoreContext';
import { IWebSocketClient } from './services/interfaces';
import { IGameStore } from './contexts/GameStoreContext';

// Helper to create a mock WebSocket client
function createMockWebSocketClient(): IWebSocketClient {
  const handlers = new Map<string, Set<any>>();

  return {
    connect: vi.fn().mockResolvedValue(undefined),
    send: vi.fn(),
    sendMessage: vi.fn((msg: { type: string; data: any }) => {
      // sendMessage is just an alias for send in the real implementation
    }),
    on: vi.fn((type: string, handler: any) => {
      if (!handlers.has(type)) {
        handlers.set(type, new Set());
      }
      handlers.get(type)!.add(handler);
    }),
    off: vi.fn((type: string, handler: any) => {
      const typeHandlers = handlers.get(type);
      if (typeHandlers) {
        typeHandlers.delete(handler);
      }
    }),
    disconnect: vi.fn(),
    isConnected: vi.fn().mockReturnValue(true),
    _handlers: handlers, // For test assertions
    _simulateMessage: (type: string, data: any) => {
      const typeHandlers = handlers.get(type);
      if (typeHandlers) {
        typeHandlers.forEach((handler) => handler({ type, data }));
      }
    },
  } as any;
}

// Helper to create a mock game store
function createMockGameStore(): IGameStore {
  return {
    npcs: [],
    setNPCs: vi.fn(),
    getNPC: vi.fn(),
    updateNPC: vi.fn(),
    windows: [],
    nextZIndex: 100,
    openWindow: vi.fn(),
    closeWindow: vi.fn(),
    minimizeWindow: vi.fn(),
    restoreWindow: vi.fn(),
    focusWindow: vi.fn(),
    updateWindow: vi.fn(),
    systemStatus: null,
    setSystemStatus: vi.fn(),
    connected: false,
    setConnected: vi.fn(),
  };
}

// Helper to render App with all necessary providers
function renderApp(mockWsClient?: IWebSocketClient, mockStore?: IGameStore) {
  const wsClient = mockWsClient || createMockWebSocketClient();
  const store = mockStore || createMockGameStore();

  return {
    ...render(
      <WebSocketProvider client={wsClient}>
        <GameStoreProvider store={store}>
          <App />
        </GameStoreProvider>
      </WebSocketProvider>
    ),
    wsClient,
    store,
  };
}

describe('App', () => {
  let originalConsoleError: any;
  let originalFetch: any;

  beforeEach(() => {
    // Suppress console errors during tests
    originalConsoleError = console.error;
    console.error = vi.fn();

    // Mock fetch to prevent API calls
    originalFetch = global.fetch;
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve([]),
      } as Response)
    );
  });

  afterEach(() => {
    console.error = originalConsoleError;
    global.fetch = originalFetch;
  });

  describe('Initial Loading State', () => {
    it('should show loading state initially', () => {
      const wsClient = createMockWebSocketClient();
      // Make connect promise never resolve to keep loading state
      wsClient.connect = vi.fn(() => new Promise(() => {}));

      renderApp(wsClient);

      expect(screen.getByText('Recursive://Neon')).toBeInTheDocument();
      expect(screen.getByText('Initializing...')).toBeInTheDocument();
      expect(screen.getByText('⚡')).toBeInTheDocument();
    });
  });

  describe('Error State', () => {
    it('should show error state when connection fails', async () => {
      const wsClient = createMockWebSocketClient();
      wsClient.connect = vi.fn().mockRejectedValue(new Error('Connection failed'));

      renderApp(wsClient);

      await waitFor(() => {
        expect(screen.getByText('Connection Error')).toBeInTheDocument();
      });

      expect(screen.getByText(/Failed to connect to server/)).toBeInTheDocument();
      expect(screen.getByText('Retry')).toBeInTheDocument();
    });
  });

  describe('Successful Initialization', () => {
    it('should connect to WebSocket on mount', async () => {
      const wsClient = createMockWebSocketClient();
      const { store } = renderApp(wsClient);

      await waitFor(() => {
        expect(wsClient.connect).toHaveBeenCalled();
      });

      await waitFor(() => {
        expect(store.setConnected).toHaveBeenCalledWith(true);
      });
    });

    it('should request initial data after connecting', async () => {
      const wsClient = createMockWebSocketClient();
      renderApp(wsClient);

      await waitFor(() => {
        expect(wsClient.send).toHaveBeenCalledWith('get_npcs', {});
      });

      await waitFor(() => {
        expect(wsClient.send).toHaveBeenCalledWith('get_status', {});
      });
    });

    it('should register WebSocket message handlers', async () => {
      const wsClient = createMockWebSocketClient();
      renderApp(wsClient);

      await waitFor(() => {
        expect(wsClient.connect).toHaveBeenCalled();
      });

      // Check that handlers were registered
      await waitFor(() => {
        expect(wsClient.on).toHaveBeenCalledWith('npcs_list', expect.any(Function));
      });

      expect(wsClient.on).toHaveBeenCalledWith('status', expect.any(Function));
      expect(wsClient.on).toHaveBeenCalledWith('error', expect.any(Function));
      expect(wsClient.on).toHaveBeenCalledWith('notification_created', expect.any(Function));
      expect(wsClient.on).toHaveBeenCalledWith('notification_updated', expect.any(Function));
      expect(wsClient.on).toHaveBeenCalledWith('notification_deleted', expect.any(Function));
      expect(wsClient.on).toHaveBeenCalledWith('notifications_cleared', expect.any(Function));
      expect(wsClient.on).toHaveBeenCalledWith('notification_config_updated', expect.any(Function));
      expect(wsClient.on).toHaveBeenCalledWith('time_response', expect.any(Function));
      expect(wsClient.on).toHaveBeenCalledWith('time_update', expect.any(Function));
      expect(wsClient.on).toHaveBeenCalledWith('settings_response', expect.any(Function));
      expect(wsClient.on).toHaveBeenCalledWith('setting_update', expect.any(Function));
      expect(wsClient.on).toHaveBeenCalledWith('settings_update', expect.any(Function));
    });

    it('should handle npcs_list message and update store', async () => {
      const wsClient = createMockWebSocketClient();
      const { store } = renderApp(wsClient);

      await waitFor(() => {
        expect(wsClient.connect).toHaveBeenCalled();
      });

      // Simulate receiving npcs_list message
      const mockNPCs = [
        { id: 'npc1', name: 'Test NPC 1' },
        { id: 'npc2', name: 'Test NPC 2' },
      ];

      (wsClient as any)._simulateMessage('npcs_list', { npcs: mockNPCs });

      await waitFor(() => {
        expect(store.setNPCs).toHaveBeenCalledWith(mockNPCs);
      });
    });

    it('should handle status message and update store', async () => {
      const wsClient = createMockWebSocketClient();
      const { store } = renderApp(wsClient);

      await waitFor(() => {
        expect(wsClient.connect).toHaveBeenCalled();
      });

      const mockStatus = {
        system: { status: 'ready', ollama_running: true },
      };

      (wsClient as any)._simulateMessage('status', mockStatus);

      await waitFor(() => {
        expect(store.setSystemStatus).toHaveBeenCalledWith(mockStatus);
      });
    });
  });

  describe('Cleanup', () => {
    it('should disconnect WebSocket on unmount', async () => {
      const wsClient = createMockWebSocketClient();
      const { unmount } = renderApp(wsClient);

      await waitFor(() => {
        expect(wsClient.connect).toHaveBeenCalled();
      });

      unmount();

      expect(wsClient.disconnect).toHaveBeenCalled();
    });

    it('should remove all event handlers on unmount', async () => {
      const wsClient = createMockWebSocketClient();
      const { unmount } = renderApp(wsClient);

      await waitFor(() => {
        expect(wsClient.connect).toHaveBeenCalled();
      });

      unmount();

      // Check that handlers were removed
      expect(wsClient.off).toHaveBeenCalledWith('notification_created', expect.any(Function));
      expect(wsClient.off).toHaveBeenCalledWith('notification_updated', expect.any(Function));
      expect(wsClient.off).toHaveBeenCalledWith('notification_deleted', expect.any(Function));
      expect(wsClient.off).toHaveBeenCalledWith('notifications_cleared', expect.any(Function));
      expect(wsClient.off).toHaveBeenCalledWith('notification_config_updated', expect.any(Function));
    });
  });
});
