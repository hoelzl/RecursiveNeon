/**
 * Tests for useAppInitialization hook
 */

import React, { ReactNode } from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useAppInitialization } from '../useAppInitialization';
import { WebSocketProvider } from '../../contexts/WebSocketContext';
import { GameStoreProvider } from '../../contexts/GameStoreContext';
import { IWebSocketClient } from '../../services/interfaces';
import { IGameStore } from '../../contexts/GameStoreContext';

// Mock the services
vi.mock('../../services/timeService', () => ({
  timeService: {
    initialize: vi.fn(),
    destroy: vi.fn(),
    handleTimeUpdate: vi.fn(),
  },
}));

vi.mock('../../services/settingsService', () => ({
  settingsService: {
    initialize: vi.fn(),
    handleSettingsResponse: vi.fn(),
    handleSettingUpdate: vi.fn(),
    handleSettingsUpdate: vi.fn(),
  },
}));

// Mock notification store
vi.mock('../../stores/notificationStore', () => ({
  useNotificationStore: vi.fn(() => ({
    loadHistory: vi.fn(),
    loadConfig: vi.fn(),
    handleNotificationCreated: vi.fn(),
    handleNotificationUpdated: vi.fn(),
    handleNotificationDeleted: vi.fn(),
    handleNotificationsCleared: vi.fn(),
    handleConfigUpdated: vi.fn(),
  })),
}));

function createMockWebSocketClient(): IWebSocketClient {
  return {
    connect: vi.fn().mockResolvedValue(undefined),
    send: vi.fn(),
    sendMessage: vi.fn(),
    on: vi.fn(),
    off: vi.fn(),
    disconnect: vi.fn(),
    isConnected: vi.fn().mockReturnValue(true),
  } as any;
}

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

function createWrapper(wsClient: IWebSocketClient, store: IGameStore) {
  return ({ children }: { children: ReactNode }) => (
    <WebSocketProvider client={wsClient}>
      <GameStoreProvider store={store}>
        {children}
      </GameStoreProvider>
    </WebSocketProvider>
  );
}

describe('useAppInitialization', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock fetch
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve([]),
      } as Response)
    );
  });

  it('should start in loading state', () => {
    const wsClient = createMockWebSocketClient();
    // Make connect never resolve to keep loading state
    wsClient.connect = vi.fn(() => new Promise(() => {}));
    const store = createMockGameStore();
    const wrapper = createWrapper(wsClient, store);

    const { result } = renderHook(() => useAppInitialization(), { wrapper });

    expect(result.current.loading).toBe(true);
    expect(result.current.error).toBe(null);
  });

  it('should connect to WebSocket on mount', async () => {
    const wsClient = createMockWebSocketClient();
    const store = createMockGameStore();
    const wrapper = createWrapper(wsClient, store);

    renderHook(() => useAppInitialization(), { wrapper });

    await waitFor(() => {
      expect(wsClient.connect).toHaveBeenCalled();
    });
  });

  it('should set connected state after successful connection', async () => {
    const wsClient = createMockWebSocketClient();
    const store = createMockGameStore();
    const wrapper = createWrapper(wsClient, store);

    renderHook(() => useAppInitialization(), { wrapper });

    await waitFor(() => {
      expect(store.setConnected).toHaveBeenCalledWith(true);
    });
  });

  it('should request initial data after connecting', async () => {
    const wsClient = createMockWebSocketClient();
    const store = createMockGameStore();
    const wrapper = createWrapper(wsClient, store);

    renderHook(() => useAppInitialization(), { wrapper });

    await waitFor(() => {
      expect(wsClient.send).toHaveBeenCalledWith('get_npcs', {});
    });

    expect(wsClient.send).toHaveBeenCalledWith('get_status', {});
  });

  it('should clear loading state after successful initialization', async () => {
    const wsClient = createMockWebSocketClient();
    const store = createMockGameStore();
    const wrapper = createWrapper(wsClient, store);

    const { result } = renderHook(() => useAppInitialization(), { wrapper });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBe(null);
  });

  it('should set error state when connection fails', async () => {
    const wsClient = createMockWebSocketClient();
    wsClient.connect = vi.fn().mockRejectedValue(new Error('Connection failed'));
    const store = createMockGameStore();
    const wrapper = createWrapper(wsClient, store);

    const { result } = renderHook(() => useAppInitialization(), { wrapper });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toContain('Failed to connect to server');
  });

  it('should provide retryConnection function', async () => {
    const wsClient = createMockWebSocketClient();
    wsClient.connect = vi.fn().mockRejectedValue(new Error('Connection failed'));
    const store = createMockGameStore();
    const wrapper = createWrapper(wsClient, store);

    const { result } = renderHook(() => useAppInitialization(), { wrapper });

    await waitFor(() => {
      expect(result.current.error).not.toBe(null);
    });

    // Retry should be a function
    expect(typeof result.current.retryConnection).toBe('function');

    // Make connection succeed on retry
    wsClient.connect = vi.fn().mockResolvedValue(undefined);

    // Call retry
    result.current.retryConnection();

    await waitFor(() => {
      expect(wsClient.connect).toHaveBeenCalledTimes(2); // Initial + retry
    });
  });
});
