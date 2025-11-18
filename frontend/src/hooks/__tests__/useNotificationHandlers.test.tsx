/**
 * Tests for useNotificationHandlers hook
 */

import React, { ReactNode } from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useNotificationHandlers } from '../useNotificationHandlers';
import { WebSocketProvider } from '../../contexts/WebSocketContext';
import { IWebSocketClient } from '../../services/interfaces';

// Mock notification store
const mockHandlers = {
  handleNotificationCreated: vi.fn(),
  handleNotificationUpdated: vi.fn(),
  handleNotificationDeleted: vi.fn(),
  handleNotificationsCleared: vi.fn(),
  handleConfigUpdated: vi.fn(),
};

vi.mock('../../stores/notificationStore', () => ({
  useNotificationStore: vi.fn(() => mockHandlers),
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

function createWrapper(wsClient: IWebSocketClient) {
  return ({ children }: { children: ReactNode }) => (
    <WebSocketProvider client={wsClient}>
      {children}
    </WebSocketProvider>
  );
}

describe('useNotificationHandlers', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should register notification handlers on mount', () => {
    const wsClient = createMockWebSocketClient();
    const wrapper = createWrapper(wsClient);

    renderHook(() => useNotificationHandlers(), { wrapper });

    // Check that all notification handlers were registered
    expect(wsClient.on).toHaveBeenCalledWith('notification_created', expect.any(Function));
    expect(wsClient.on).toHaveBeenCalledWith('notification_updated', expect.any(Function));
    expect(wsClient.on).toHaveBeenCalledWith('notification_deleted', expect.any(Function));
    expect(wsClient.on).toHaveBeenCalledWith('notifications_cleared', expect.any(Function));
    expect(wsClient.on).toHaveBeenCalledWith('notification_config_updated', expect.any(Function));
  });

  it('should remove all notification handlers on unmount', () => {
    const wsClient = createMockWebSocketClient();
    const wrapper = createWrapper(wsClient);

    const { unmount } = renderHook(() => useNotificationHandlers(), { wrapper });

    unmount();

    // Check that all notification handlers were removed
    expect(wsClient.off).toHaveBeenCalledWith('notification_created', expect.any(Function));
    expect(wsClient.off).toHaveBeenCalledWith('notification_updated', expect.any(Function));
    expect(wsClient.off).toHaveBeenCalledWith('notification_deleted', expect.any(Function));
    expect(wsClient.off).toHaveBeenCalledWith('notifications_cleared', expect.any(Function));
    expect(wsClient.off).toHaveBeenCalledWith('notification_config_updated', expect.any(Function));
  });

  it('should call handleNotificationCreated when notification_created message is received', () => {
    const wsClient = createMockWebSocketClient();
    const wrapper = createWrapper(wsClient);

    renderHook(() => useNotificationHandlers(), { wrapper });

    // Get the registered handler
    const onCall = (wsClient.on as any).mock.calls.find(
      (call: any) => call[0] === 'notification_created'
    );
    const handler = onCall[1];

    // Simulate message
    const mockNotification = { id: 'notif1', title: 'Test' };
    handler({ data: mockNotification });

    expect(mockHandlers.handleNotificationCreated).toHaveBeenCalledWith(mockNotification);
  });

  it('should call handleNotificationUpdated when notification_updated message is received', () => {
    const wsClient = createMockWebSocketClient();
    const wrapper = createWrapper(wsClient);

    renderHook(() => useNotificationHandlers(), { wrapper });

    const onCall = (wsClient.on as any).mock.calls.find(
      (call: any) => call[0] === 'notification_updated'
    );
    const handler = onCall[1];

    const mockNotification = { id: 'notif1', title: 'Updated' };
    handler({ data: mockNotification });

    expect(mockHandlers.handleNotificationUpdated).toHaveBeenCalledWith(mockNotification);
  });

  it('should call handleNotificationDeleted when notification_deleted message is received', () => {
    const wsClient = createMockWebSocketClient();
    const wrapper = createWrapper(wsClient);

    renderHook(() => useNotificationHandlers(), { wrapper });

    const onCall = (wsClient.on as any).mock.calls.find(
      (call: any) => call[0] === 'notification_deleted'
    );
    const handler = onCall[1];

    handler({ data: { id: 'notif1' } });

    expect(mockHandlers.handleNotificationDeleted).toHaveBeenCalledWith('notif1');
  });

  it('should call handleNotificationsCleared when notifications_cleared message is received', () => {
    const wsClient = createMockWebSocketClient();
    const wrapper = createWrapper(wsClient);

    renderHook(() => useNotificationHandlers(), { wrapper });

    const onCall = (wsClient.on as any).mock.calls.find(
      (call: any) => call[0] === 'notifications_cleared'
    );
    const handler = onCall[1];

    handler({ data: {} });

    expect(mockHandlers.handleNotificationsCleared).toHaveBeenCalled();
  });

  it('should call handleConfigUpdated when notification_config_updated message is received', () => {
    const wsClient = createMockWebSocketClient();
    const wrapper = createWrapper(wsClient);

    renderHook(() => useNotificationHandlers(), { wrapper });

    const onCall = (wsClient.on as any).mock.calls.find(
      (call: any) => call[0] === 'notification_config_updated'
    );
    const handler = onCall[1];

    const mockConfig = { position: 'top-right' };
    handler({ data: mockConfig });

    expect(mockHandlers.handleConfigUpdated).toHaveBeenCalledWith(mockConfig);
  });
});
