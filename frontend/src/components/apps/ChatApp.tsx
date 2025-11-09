/**
 * Chat App - NPC conversation interface
 */

import { useState, useEffect, useRef } from 'react';
import { useGameStore } from '../../stores/gameStore';
import { wsClient } from '../../services/websocket';
import { NPC, ChatMessage as ChatMessageType } from '../../types';

interface Message {
  sender: 'user' | 'npc';
  content: string;
  npcName?: string;
}

export function ChatApp() {
  const { npcs, updateNPC } = useGameStore();
  const [selectedNPC, setSelectedNPC] = useState<NPC | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Listen for chat responses
    const handleChatResponse = (msg: any) => {
      const data: ChatMessageType = msg.data;
      setMessages((prev) => [
        ...prev,
        {
          sender: 'npc',
          content: data.message,
          npcName: data.npc_name,
        },
      ]);
      setSending(false);

      // Update NPC's conversation history in the store
      if (selectedNPC && data.npc_id === selectedNPC.id) {
        const newMessage = {
          role: 'assistant' as const,
          content: data.message,
          timestamp: data.timestamp,
        };
        updateNPC(selectedNPC.id, {
          memory: {
            ...selectedNPC.memory,
            conversation_history: [...selectedNPC.memory.conversation_history, newMessage],
          },
        });
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
  }, [selectedNPC, updateNPC]);

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
    } else {
      setMessages([]);
    }
  }, [selectedNPC?.id]);

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

    // Restore focus to input field
    setTimeout(() => {
      inputRef.current?.focus();
    }, 0);
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
            className={`chat-npc-item ${selectedNPC?.id === npc.id ? 'active' : ''}`}
            onClick={() => setSelectedNPC(npc)}
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
