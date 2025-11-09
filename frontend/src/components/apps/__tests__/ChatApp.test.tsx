/**
 * Unit tests for ChatApp component
 *
 * These tests demonstrate the improved testability after refactoring for
 * dependency injection. ChatApp can now be tested in complete isolation
 * without requiring a real WebSocket connection or global store.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatApp } from '../ChatApp';
import { WebSocketProvider } from '../../../contexts/WebSocketContext';
import { GameStoreProvider } from '../../../contexts/GameStoreContext';
import { IWebSocketClient } from '../../../services/interfaces';
import { IGameStore } from '../../../contexts/GameStoreContext';
import { NPC } from '../../../types';

// Helper function to create a mock WebSocket client
function createMockWebSocketClient(): IWebSocketClient {
  const handlers = new Map<string, Set<any>>();

  return {
    connect: vi.fn().mockResolvedValue(undefined),
    send: vi.fn(),
    on: vi.fn((type: string, handler: any) => {
      if (!handlers.has(type)) {
        handlers.set(type, new Set());
      }
      handlers.get(type)!.add(handler);
    }),
    off: vi.fn((type: string, handler: any) => {
      const typeHandlers = handlers.get(type);
      if (typeHandlers) {
        typeHandlers.delete(handler);
      }
    }),
    disconnect: vi.fn(),
    isConnected: vi.fn().mockReturnValue(true),
    // Helper method to simulate receiving messages (not part of interface)
    _simulateMessage: (type: string, data: any) => {
      const typeHandlers = handlers.get(type);
      if (typeHandlers) {
        typeHandlers.forEach((handler) => handler({ type, data }));
      }
    },
  } as any;
}

// Helper function to create a mock game store
function createMockGameStore(npcs: NPC[] = []): IGameStore {
  let currentNPCs = [...npcs];

  return {
    npcs: currentNPCs,
    setNPCs: vi.fn((newNPCs) => {
      currentNPCs = newNPCs;
    }),
    getNPC: vi.fn((id: string) => currentNPCs.find((npc) => npc.id === id)),
    updateNPC: vi.fn((id: string, updates: Partial<NPC>) => {
      const index = currentNPCs.findIndex((npc) => npc.id === id);
      if (index !== -1) {
        currentNPCs[index] = { ...currentNPCs[index], ...updates };
      }
    }),
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

// Helper function to create a sample NPC for testing
function createSampleNPC(id: string = 'test-npc'): NPC {
  return {
    id,
    name: 'Test NPC',
    personality: 'friendly',
    role: 'informant',
    background: 'A helpful test NPC',
    occupation: 'Tester',
    location: 'Test Suite',
    greeting: 'Hello, test!',
    conversation_style: 'helpful and clear',
    topics_of_interest: ['testing', 'quality assurance'],
    secrets: [],
    avatar: '👤',
    theme_color: '#4a9eff',
    memory: {
      npc_id: id,
      conversation_history: [],
      facts_learned: [],
      relationship_level: 0,
      last_interaction: null,
    },
  };
}

// Helper function to render ChatApp with mock providers
function renderChatApp(mockStore?: IGameStore, mockWsClient?: IWebSocketClient) {
  const store = mockStore || createMockGameStore();
  const wsClient = mockWsClient || createMockWebSocketClient();

  return {
    ...render(
      <WebSocketProvider client={wsClient}>
        <GameStoreProvider store={store}>
          <ChatApp />
        </GameStoreProvider>
      </WebSocketProvider>
    ),
    store,
    wsClient,
  };
}

describe('ChatApp', () => {
  describe('Initial Render', () => {
    it('should render empty state when no NPCs', () => {
      renderChatApp();

      expect(screen.getByText('Select an NPC to start chatting')).toBeInTheDocument();
      expect(screen.getByText('💬')).toBeInTheDocument();
    });

    it('should render NPC list when NPCs are available', () => {
      const npc1 = createSampleNPC('npc1');
      npc1.name = 'Alice';
      const npc2 = createSampleNPC('npc2');
      npc2.name = 'Bob';

      const store = createMockGameStore([npc1, npc2]);
      renderChatApp(store);

      expect(screen.getByText('Alice')).toBeInTheDocument();
      expect(screen.getByText('Bob')).toBeInTheDocument();
    });
  });

  describe('NPC Selection', () => {
    it('should show chat interface when NPC is selected', () => {
      const npc = createSampleNPC();
      const store = createMockGameStore([npc]);
      renderChatApp(store);

      // Click on NPC
      fireEvent.click(screen.getByText('Test NPC'));

      // Should show input field
      expect(screen.getByPlaceholderText('Message Test NPC...')).toBeInTheDocument();
      expect(screen.getByText('Send')).toBeInTheDocument();
    });

    it('should load conversation history when NPC is selected', () => {
      const npc = createSampleNPC();
      npc.memory.conversation_history = [
        { role: 'user', content: 'Hello!', timestamp: '2024-01-01T00:00:00Z' },
        { role: 'assistant', content: 'Hi there!', timestamp: '2024-01-01T00:00:01Z' },
      ];

      const store = createMockGameStore([npc]);
      renderChatApp(store);

      // Select NPC
      fireEvent.click(screen.getByText('Test NPC'));

      // Should display conversation history
      expect(screen.getByText('Hello!')).toBeInTheDocument();
      expect(screen.getByText('Hi there!')).toBeInTheDocument();
    });
  });

  describe('Sending Messages', () => {
    it('should send message via WebSocket when user clicks Send', async () => {
      const npc = createSampleNPC();
      const store = createMockGameStore([npc]);
      const wsClient = createMockWebSocketClient();
      renderChatApp(store, wsClient);

      // Select NPC
      fireEvent.click(screen.getByText('Test NPC'));

      // Type message
      const input = screen.getByPlaceholderText('Message Test NPC...');
      fireEvent.change(input, { target: { value: 'Hello NPC!' } });

      // Click send
      fireEvent.click(screen.getByText('Send'));

      // Verify WebSocket send was called
      expect(wsClient.send).toHaveBeenCalledWith('chat', {
        npc_id: npc.id,
        message: 'Hello NPC!',
        player_id: 'player_1',
      });
    });

    it('should add user message to UI immediately', () => {
      const npc = createSampleNPC();
      const store = createMockGameStore([npc]);
      renderChatApp(store);

      // Select NPC and send message
      fireEvent.click(screen.getByText('Test NPC'));
      const input = screen.getByPlaceholderText('Message Test NPC...');
      fireEvent.change(input, { target: { value: 'Test message' } });
      fireEvent.click(screen.getByText('Send'));

      // Message should appear in UI
      expect(screen.getByText('Test message')).toBeInTheDocument();
    });

    it('should clear input field after sending', () => {
      const npc = createSampleNPC();
      const store = createMockGameStore([npc]);
      renderChatApp(store);

      fireEvent.click(screen.getByText('Test NPC'));
      const input = screen.getByPlaceholderText('Message Test NPC...') as HTMLInputElement;
      fireEvent.change(input, { target: { value: 'Test message' } });
      fireEvent.click(screen.getByText('Send'));

      expect(input.value).toBe('');
    });

    it('should show "Thinking..." indicator while waiting for response', () => {
      const npc = createSampleNPC();
      const store = createMockGameStore([npc]);
      renderChatApp(store);

      fireEvent.click(screen.getByText('Test NPC'));
      const input = screen.getByPlaceholderText('Message Test NPC...');
      fireEvent.change(input, { target: { value: 'Test' } });
      fireEvent.click(screen.getByText('Send'));

      expect(screen.getByText('Thinking...')).toBeInTheDocument();
    });
  });

  describe('Receiving Messages', () => {
    it('should display NPC response when received via WebSocket', async () => {
      const npc = createSampleNPC();
      const store = createMockGameStore([npc]);
      const wsClient = createMockWebSocketClient();
      renderChatApp(store, wsClient);

      // Select NPC
      fireEvent.click(screen.getByText('Test NPC'));

      // Simulate receiving a chat response
      (wsClient as any)._simulateMessage('chat_response', {
        npc_id: npc.id,
        npc_name: npc.name,
        message: 'Hello! How can I help you?',
        timestamp: new Date().toISOString(),
      });

      // Wait for the message to appear
      await waitFor(() => {
        expect(screen.getByText('Hello! How can I help you?')).toBeInTheDocument();
      });
    });

    it('should update NPC memory when receiving response', async () => {
      const npc = createSampleNPC();
      const store = createMockGameStore([npc]);
      const wsClient = createMockWebSocketClient();
      renderChatApp(store, wsClient);

      fireEvent.click(screen.getByText('Test NPC'));

      const responseMessage = 'Test response';
      (wsClient as any)._simulateMessage('chat_response', {
        npc_id: npc.id,
        npc_name: npc.name,
        message: responseMessage,
        timestamp: new Date().toISOString(),
      });

      await waitFor(() => {
        expect(store.updateNPC).toHaveBeenCalledWith(
          npc.id,
          expect.objectContaining({
            memory: expect.objectContaining({
              conversation_history: expect.arrayContaining([
                expect.objectContaining({
                  role: 'assistant',
                  content: responseMessage,
                }),
              ]),
            }),
          })
        );
      });
    });
  });

  describe('Keyboard Shortcuts', () => {
    it('should send message when Enter key is pressed', () => {
      const npc = createSampleNPC();
      const store = createMockGameStore([npc]);
      const wsClient = createMockWebSocketClient();
      renderChatApp(store, wsClient);

      fireEvent.click(screen.getByText('Test NPC'));
      const input = screen.getByPlaceholderText('Message Test NPC...');
      fireEvent.change(input, { target: { value: 'Test message' } });
      fireEvent.keyPress(input, { key: 'Enter', code: 'Enter', charCode: 13 });

      expect(wsClient.send).toHaveBeenCalled();
    });

    it('should not send message when Shift+Enter is pressed', () => {
      const npc = createSampleNPC();
      const store = createMockGameStore([npc]);
      const wsClient = createMockWebSocketClient();
      renderChatApp(store, wsClient);

      fireEvent.click(screen.getByText('Test NPC'));
      const input = screen.getByPlaceholderText('Message Test NPC...');
      fireEvent.change(input, { target: { value: 'Test message' } });
      fireEvent.keyPress(input, { key: 'Enter', code: 'Enter', charCode: 13, shiftKey: true });

      expect(wsClient.send).not.toHaveBeenCalled();
    });
  });

  describe('Edge Cases', () => {
    it('should not send empty messages', () => {
      const npc = createSampleNPC();
      const store = createMockGameStore([npc]);
      const wsClient = createMockWebSocketClient();
      renderChatApp(store, wsClient);

      fireEvent.click(screen.getByText('Test NPC'));
      fireEvent.click(screen.getByText('Send'));

      expect(wsClient.send).not.toHaveBeenCalled();
    });

    it('should trim whitespace from messages', () => {
      const npc = createSampleNPC();
      const store = createMockGameStore([npc]);
      const wsClient = createMockWebSocketClient();
      renderChatApp(store, wsClient);

      fireEvent.click(screen.getByText('Test NPC'));
      const input = screen.getByPlaceholderText('Message Test NPC...');
      fireEvent.change(input, { target: { value: '  Hello  ' } });
      fireEvent.click(screen.getByText('Send'));

      expect(wsClient.send).toHaveBeenCalledWith('chat', expect.objectContaining({
        message: 'Hello',
      }));
    });
  });
});
