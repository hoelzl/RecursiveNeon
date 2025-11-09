/**
 * WebSocket Context Provider for Dependency Injection
 *
 * This context allows components to access the WebSocket client
 * without directly importing the singleton, enabling:
 * - Easy testing with mock WebSocket clients
 * - Proper dependency injection
 * - Better separation of concerns
 */

import React, { createContext, useContext, ReactNode } from 'react';
import { IWebSocketClient } from '../services/interfaces';

const WebSocketContext = createContext<IWebSocketClient | null>(null);

interface WebSocketProviderProps {
  client: IWebSocketClient;
  children: ReactNode;
}

/**
 * Provider component that makes WebSocket client available to all children
 */
export function WebSocketProvider({ client, children }: WebSocketProviderProps) {
  return (
    <WebSocketContext.Provider value={client}>
      {children}
    </WebSocketContext.Provider>
  );
}

/**
 * Hook to access the WebSocket client from context
 *
 * @throws Error if used outside of WebSocketProvider
 */
export function useWebSocket(): IWebSocketClient {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
}
