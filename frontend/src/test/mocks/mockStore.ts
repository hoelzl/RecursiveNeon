/**
 * Mock store for testing
 *
 * Provides a testable Zustand store implementation that can be used
 * in component tests without side effects.
 */
import { vi } from 'vitest';

/**
 * Creates a mock game store for testing
 */
export function createMockStore(initialState = {}) {
  const defaultState = {
    windows: [],
    npcs: [],
    activeNpcId: null,
    chatHistory: {},
    ...initialState,
  };

  let state = { ...defaultState };
  const subscribers = new Set<Function>();

  const store = {
    getState: vi.fn(() => state),

    setState: vi.fn((partial: any) => {
      state = { ...state, ...(typeof partial === 'function' ? partial(state) : partial) };
      subscribers.forEach((subscriber) => subscriber(state));
    }),

    subscribe: vi.fn((subscriber: Function) => {
      subscribers.add(subscriber);
      return () => subscribers.delete(subscriber);
    }),

    // Helper methods for testing
    reset: () => {
      state = { ...defaultState };
      subscribers.forEach((subscriber) => subscriber(state));
    },

    // Expose state for testing
    __getState: () => state,
  };

  return store;
}
