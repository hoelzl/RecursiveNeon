/**
 * Global game state store using Zustand
 */

import { create } from 'zustand';
import { NPC, WindowState, SystemStatus } from '../types';

interface GameStore {
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

export const useGameStore = create<GameStore>((set, get) => ({
  // NPCs
  npcs: [],
  setNPCs: (npcs) => set({ npcs }),
  getNPC: (id) => get().npcs.find((npc) => npc.id === id),
  updateNPC: (id, updates) => {
    set((state) => ({
      npcs: state.npcs.map((npc) =>
        npc.id === id ? { ...npc, ...updates } : npc
      ),
    }));
  },

  // Windows
  windows: [],
  nextZIndex: 100,

  openWindow: (windowData) => {
    const { windows, nextZIndex } = get();
    const id = `window-${Date.now()}-${Math.random()}`;
    const newWindow: WindowState = {
      ...windowData,
      id,
      zIndex: nextZIndex,
      minimized: false,
    };
    set({
      windows: [...windows, newWindow],
      nextZIndex: nextZIndex + 1,
    });
  },

  closeWindow: (id) => {
    set((state) => ({
      windows: state.windows.filter((w) => w.id !== id),
    }));
  },

  minimizeWindow: (id) => {
    set((state) => ({
      windows: state.windows.map((w) =>
        w.id === id ? { ...w, minimized: true } : w
      ),
    }));
  },

  restoreWindow: (id) => {
    const { windows, nextZIndex } = get();
    set({
      windows: windows.map((w) =>
        w.id === id ? { ...w, minimized: false, zIndex: nextZIndex } : w
      ),
      nextZIndex: nextZIndex + 1,
    });
  },

  focusWindow: (id) => {
    const { windows, nextZIndex } = get();
    set({
      windows: windows.map((w) =>
        w.id === id ? { ...w, zIndex: nextZIndex } : w
      ),
      nextZIndex: nextZIndex + 1,
    });
  },

  updateWindow: (id, updates) => {
    set((state) => ({
      windows: state.windows.map((w) =>
        w.id === id ? { ...w, ...updates } : w
      ),
    }));
  },

  // System status
  systemStatus: null,
  setSystemStatus: (status) => set({ systemStatus: status }),

  // Connection
  connected: false,
  setConnected: (connected) => set({ connected }),
}));
