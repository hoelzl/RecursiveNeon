/**
 * Chat App - NPC conversation interface
 *
 * Refactored for testability using dependency injection through React Context.
 * Dependencies are injected via context providers instead of direct imports.
 */

import { useState, useEffect, useRef } from 'react';
import { useGameStoreContext } from '../../contexts/GameStoreContext';
import { useWebSocket } from '../../contexts/WebSocketContext';
import { ChatMessage as ChatMessageType } from '../../types';

interface Message {
  sender: 'user' | 'npc';
  content: string;
  npcName?: string;
}

export function ChatApp() {
  // Inject dependencies via context providers
  const { npcs, updateNPC, getNPC } = useGameStoreContext();
  const wsClient = useWebSocket();

  const [selectedNPCId, setSelectedNPCId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Get the current NPC from store (always fresh)
  const selectedNPC = selectedNPCId ? getNPC(selectedNPCId) : null;

  useEffect(() => {
    // Listen for chat responses
    const handleChatResponse = (msg: any) => {
      const data: ChatMessageType = msg.data;

      // Get the NPC that sent this message (not the currently selected one)
      const messageNPC = getNPC(data.npc_id);

      if (messageNPC) {
        // Always save the message to the correct NPC's conversation history
        const newMessage = {
          role: 'assistant' as const,
          content: data.message,
          timestamp: data.timestamp,
        };
        updateNPC(messageNPC.id, {
          memory: {
            ...messageNPC.memory,
            conversation_history: [...messageNPC.memory.conversation_history, newMessage],
          },
        });

        // Only add to UI if this message is for the currently selected NPC
        if (selectedNPCId === data.npc_id) {
          setMessages((prev) => [
            ...prev,
            {
              sender: 'npc',
              content: data.message,
              npcName: data.npc_name,
            },
          ]);
        }
      }

      // Always clear sending state when any response is received
      setSending(false);

      // Restore focus to input field after response (only if this is the selected NPC)
      if (selectedNPCId === data.npc_id) {
        setTimeout(() => {
          inputRef.current?.focus();
        }, 100);
      }
    };

    const handleChatThinking = () => {
      setSending(true);
    };

    wsClient.on('chat_response', handleChatResponse);
    wsClient.on('chat_thinking', handleChatThinking);

    return () => {
      wsClient.off('chat_response', handleChatResponse);
      wsClient.off('chat_thinking', handleChatThinking);
    };
  }, [selectedNPCId, getNPC, updateNPC, inputRef]);

  useEffect(() => {
    // Auto-scroll to bottom
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    // Load conversation history when selecting new NPC
    if (selectedNPC) {
      const history = selectedNPC.memory.conversation_history.map((msg) => ({
        sender: msg.role === 'user' ? 'user' as const : 'npc' as const,
        content: msg.content,
        npcName: selectedNPC.name,
      }));
      setMessages(history);

      // Auto-focus the input field when switching to a new NPC
      setTimeout(() => {
        inputRef.current?.focus();
      }, 100);
    } else {
      setMessages([]);
    }
    // Clear sending state when switching NPCs to prevent "Thinking..." from showing in wrong chat
    setSending(false);
  }, [selectedNPCId, npcs]);

  const handleSend = () => {
    if (!input.trim() || !selectedNPC || sending) return;

    const userMessage = input.trim();

    // Add user message to UI
    setMessages((prev) => [
      ...prev,
      {
        sender: 'user',
        content: userMessage,
      },
    ]);

    // Update NPC's conversation history in the store
    const timestamp = new Date().toISOString();
    const newMessage = {
      role: 'user' as const,
      content: userMessage,
      timestamp,
    };
    updateNPC(selectedNPC.id, {
      memory: {
        ...selectedNPC.memory,
        conversation_history: [...selectedNPC.memory.conversation_history, newMessage],
      },
    });

    // Send to backend
    wsClient.send('chat', {
      npc_id: selectedNPC.id,
      message: userMessage,
      player_id: 'player_1',
    });

    setInput('');
    setSending(true);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-app" style={{ display: 'flex', height: '100%' }}>
      {/* Sidebar with NPC list */}
      <div className="chat-sidebar">
        {npcs.map((npc) => (
          <div
            key={npc.id}
            className={`chat-npc-item ${selectedNPCId === npc.id ? 'active' : ''}`}
            onClick={() => setSelectedNPCId(npc.id)}
          >
            <div className="chat-npc-avatar">{npc.avatar}</div>
            <div className="chat-npc-name">{npc.name}</div>
            <div className="chat-npc-occupation">{npc.occupation}</div>
          </div>
        ))}
      </div>

      {/* Chat area */}
      <div className="chat-main">
        {selectedNPC ? (
          <>
            <div className="chat-messages">
              {messages.map((msg, idx) => (
                <div key={idx} className={`chat-message ${msg.sender}`}>
                  <div className="chat-message-sender">
                    {msg.sender === 'user' ? 'You' : msg.npcName}
                  </div>
                  <div className="chat-message-content">{msg.content}</div>
                </div>
              ))}
              {sending && (
                <div className="chat-message npc">
                  <div className="chat-message-sender">{selectedNPC.name}</div>
                  <div className="chat-message-content">
                    <em>Thinking...</em>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="chat-input-container">
              <input
                ref={inputRef}
                type="text"
                className="chat-input"
                placeholder={`Message ${selectedNPC.name}...`}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                disabled={sending}
              />
              <button
                className="chat-send-btn"
                onClick={handleSend}
                disabled={sending || !input.trim()}
              >
                Send
              </button>
            </div>
          </>
        ) : (
          <div className="chat-empty">
            <div className="chat-empty-icon">💬</div>
            <div>Select an NPC to start chatting</div>
          </div>
        )}
      </div>
    </div>
  );
}
