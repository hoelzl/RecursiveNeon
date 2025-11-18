/**
 * Tests for useWebSocketHandlers hook
 */

import React, { ReactNode } from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useWebSocketHandlers } from '../useWebSocketHandlers';
import { WebSocketProvider } from '../../contexts/WebSocketContext';
import { GameStoreProvider } from '../../contexts/GameStoreContext';
import { IWebSocketClient } from '../../services/interfaces';
import { IGameStore } from '../../contexts/GameStoreContext';

// Mock the services
vi.mock('../../services/timeService', () => ({
  timeService: {
    handleTimeUpdate: vi.fn(),
  },
}));

vi.mock('../../services/settingsService', () => ({
  settingsService: {
    handleSettingsResponse: vi.fn(),
    handleSettingUpdate: vi.fn(),
    handleSettingsUpdate: vi.fn(),
  },
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

describe('useWebSocketHandlers', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should register WebSocket handlers on mount', () => {
    const wsClient = createMockWebSocketClient();
    const store = createMockGameStore();
    const wrapper = createWrapper(wsClient, store);

    renderHook(() => useWebSocketHandlers(), { wrapper });

    // Check that handlers were registered
    expect(wsClient.on).toHaveBeenCalledWith('npcs_list', expect.any(Function));
    expect(wsClient.on).toHaveBeenCalledWith('status', expect.any(Function));
    expect(wsClient.on).toHaveBeenCalledWith('error', expect.any(Function));
    expect(wsClient.on).toHaveBeenCalledWith('time_response', expect.any(Function));
    expect(wsClient.on).toHaveBeenCalledWith('time_update', expect.any(Function));
    expect(wsClient.on).toHaveBeenCalledWith('settings_response', expect.any(Function));
    expect(wsClient.on).toHaveBeenCalledWith('setting_update', expect.any(Function));
    expect(wsClient.on).toHaveBeenCalledWith('settings_update', expect.any(Function));
  });

  it('should remove all handlers on unmount', () => {
    const wsClient = createMockWebSocketClient();
    const store = createMockGameStore();
    const wrapper = createWrapper(wsClient, store);

    const { unmount } = renderHook(() => useWebSocketHandlers(), { wrapper });

    unmount();

    // Check that handlers were removed
    expect(wsClient.off).toHaveBeenCalledWith('npcs_list', expect.any(Function));
    expect(wsClient.off).toHaveBeenCalledWith('status', expect.any(Function));
    expect(wsClient.off).toHaveBeenCalledWith('error', expect.any(Function));
    expect(wsClient.off).toHaveBeenCalledWith('time_response', expect.any(Function));
    expect(wsClient.off).toHaveBeenCalledWith('time_update', expect.any(Function));
    expect(wsClient.off).toHaveBeenCalledWith('settings_response', expect.any(Function));
    expect(wsClient.off).toHaveBeenCalledWith('setting_update', expect.any(Function));
    expect(wsClient.off).toHaveBeenCalledWith('settings_update', expect.any(Function));
  });

  it('should call setNPCs when npcs_list message is received', () => {
    const wsClient = createMockWebSocketClient();
    const store = createMockGameStore();
    const wrapper = createWrapper(wsClient, store);

    renderHook(() => useWebSocketHandlers(), { wrapper });

    // Get the registered handler
    const onCall = (wsClient.on as any).mock.calls.find(
      (call: any) => call[0] === 'npcs_list'
    );
    const handler = onCall[1];

    // Simulate message
    const mockNPCs = [{ id: 'npc1', name: 'Test NPC' }];
    handler({ data: { npcs: mockNPCs } });

    expect(store.setNPCs).toHaveBeenCalledWith(mockNPCs);
  });

  it('should call setSystemStatus when status message is received', () => {
    const wsClient = createMockWebSocketClient();
    const store = createMockGameStore();
    const wrapper = createWrapper(wsClient, store);

    renderHook(() => useWebSocketHandlers(), { wrapper });

    // Get the registered handler
    const onCall = (wsClient.on as any).mock.calls.find(
      (call: any) => call[0] === 'status'
    );
    const handler = onCall[1];

    // Simulate message
    const mockStatus = { system: { status: 'ready' } };
    handler({ data: mockStatus });

    expect(store.setSystemStatus).toHaveBeenCalledWith(mockStatus);
  });
});
