/**
 * Mock WebSocket client for testing
 *
 * Provides a testable WebSocket implementation that can be used
 * in component tests without requiring a real WebSocket connection.
 */
import { vi } from 'vitest';

export interface MockWebSocketClient {
  connect: ReturnType<typeof vi.fn>;
  disconnect: ReturnType<typeof vi.fn>;
  send: ReturnType<typeof vi.fn>;
  on: ReturnType<typeof vi.fn>;
  off: ReturnType<typeof vi.fn>;
  isConnected: () => boolean;
  // Helpers for testing
  simulateMessage: (type: string, data: any) => void;
  simulateConnect: () => void;
  simulateDisconnect: () => void;
  simulateError: (error: Error) => void;
}

/**
 * Creates a mock WebSocket client for testing
 */
export function createMockWebSocketClient(): MockWebSocketClient {
  const eventHandlers = new Map<string, Set<Function>>();
  let connected = false;

  const mockClient: MockWebSocketClient = {
    connect: vi.fn(() => {
      connected = true;
    }),

    disconnect: vi.fn(() => {
      connected = false;
    }),

    send: vi.fn(),

    on: vi.fn((event: string, handler: Function) => {
      if (!eventHandlers.has(event)) {
        eventHandlers.set(event, new Set());
      }
      eventHandlers.get(event)!.add(handler);
    }),

    off: vi.fn((event: string, handler: Function) => {
      eventHandlers.get(event)?.delete(handler);
    }),

    isConnected: () => connected,

    // Test helpers
    simulateMessage: (type: string, data: any) => {
      const handlers = eventHandlers.get('message');
      if (handlers) {
        handlers.forEach((handler) => handler({ type, ...data }));
      }
    },

    simulateConnect: () => {
      connected = true;
      const handlers = eventHandlers.get('connect');
      if (handlers) {
        handlers.forEach((handler) => handler());
      }
    },

    simulateDisconnect: () => {
      connected = false;
      const handlers = eventHandlers.get('disconnect');
      if (handlers) {
        handlers.forEach((handler) => handler());
      }
    },

    simulateError: (error: Error) => {
      const handlers = eventHandlers.get('error');
      if (handlers) {
        handlers.forEach((handler) => handler(error));
      }
    },
  };

  return mockClient;
}
