/**
 * Service interfaces for dependency injection
 */

import { WebSocketMessage } from '../types';

export type MessageHandler = (message: WebSocketMessage) => void;

/**
 * Interface for WebSocket client to enable mocking in tests
 */
export interface IWebSocketClient {
  connect(): Promise<void>;
  send(type: string, data?: any): void;
  on(type: string, handler: MessageHandler): void;
  off(type: string, handler: MessageHandler): void;
  disconnect(): void;
  isConnected(): boolean;
}
