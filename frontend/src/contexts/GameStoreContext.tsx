/**
 * Game Store Context Provider for Dependency Injection
 *
 * This context allows components to access the game store
 * without directly importing the singleton, enabling:
 * - Easy testing with mock stores
 * - Proper dependency injection
 * - Better testability
 */

import React, { createContext, useContext, ReactNode } from 'react';
import { NPC, WindowState, SystemStatus } from '../types';

/**
 * Interface for the game store to enable mocking
 */
export interface IGameStore {
  // NPCs
  npcs: NPC[];
  setNPCs: (npcs: NPC[]) => void;
  getNPC: (id: string) => NPC | undefined;
  updateNPC: (id: string, updates: Partial<NPC>) => void;

  // Windows
  windows: WindowState[];
  nextZIndex: number;
  openWindow: (window: Omit<WindowState, 'id' | 'zIndex'>) => void;
  closeWindow: (id: string) => void;
  minimizeWindow: (id: string) => void;
  restoreWindow: (id: string) => void;
  focusWindow: (id: string) => void;
  updateWindow: (id: string, updates: Partial<WindowState>) => void;

  // System status
  systemStatus: SystemStatus | null;
  setSystemStatus: (status: SystemStatus) => void;

  // Connection status
  connected: boolean;
  setConnected: (connected: boolean) => void;
}

const GameStoreContext = createContext<IGameStore | null>(null);

interface GameStoreProviderProps {
  store: IGameStore;
  children: ReactNode;
}

/**
 * Provider component that makes game store available to all children
 */
export function GameStoreProvider({ store, children }: GameStoreProviderProps) {
  return (
    <GameStoreContext.Provider value={store}>
      {children}
    </GameStoreContext.Provider>
  );
}

/**
 * Hook to access the game store from context
 *
 * @throws Error if used outside of GameStoreProvider
 */
export function useGameStoreContext(): IGameStore {
  const context = useContext(GameStoreContext);
  if (!context) {
    throw new Error('useGameStoreContext must be used within a GameStoreProvider');
  }
  return context;
}
