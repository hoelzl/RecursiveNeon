/**
 * Root provider component that wraps the application with all necessary contexts
 *
 * This component provides:
 * - WebSocket client context
 * - Game store context
 *
 * Centralizing providers here makes it easier to:
 * - Test components with mock providers
 * - Manage dependency injection
 * - Keep the app structure clean
 */

import React, { ReactNode } from 'react';
import { WebSocketProvider } from './WebSocketContext';
import { GameStoreProvider } from './GameStoreContext';
import { wsClient } from '../services/websocket';
import { useGameStore } from '../stores/gameStore';

interface AppProvidersProps {
  children: ReactNode;
  // Allow injecting custom implementations for testing
  webSocketClient?: any;
  gameStore?: any;
}

/**
 * Wraps the application with all context providers
 *
 * In production, uses the real singleton instances.
 * In tests, accepts mock implementations via props.
 */
export function AppProviders({
  children,
  webSocketClient = wsClient,
  gameStore,
}: AppProvidersProps) {
  // If gameStore is provided (for testing), use it directly
  // Otherwise, wrap the real Zustand hook
  const GameStoreWrapper = gameStore ? (
    <GameStoreProvider store={gameStore}>
      {children}
    </GameStoreProvider>
  ) : (
    <GameStoreProviderWithHook>
      {children}
    </GameStoreProviderWithHook>
  );

  return (
    <WebSocketProvider client={webSocketClient}>
      {GameStoreWrapper}
    </WebSocketProvider>
  );
}

/**
 * Wrapper component that uses the Zustand hook and provides it via context
 */
function GameStoreProviderWithHook({ children }: { children: ReactNode }) {
  const store = useGameStore();

  return (
    <GameStoreProvider store={store}>
      {children}
    </GameStoreProvider>
  );
}
