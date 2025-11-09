/**
 * Desktop component - Main desktop environment
 */

import { useGameStore } from '../stores/gameStore';
import { Window } from './Window';
import { Taskbar } from './Taskbar';
import { ChatApp } from './apps/ChatApp';

interface DesktopIcon {
  id: string;
  label: string;
  emoji: string;
  action: () => void;
}

export function Desktop() {
  const { windows, openWindow, npcs } = useGameStore();

  const icons: DesktopIcon[] = [
    {
      id: 'chat',
      label: 'Chat',
      emoji: '💬',
      action: () => {
        openWindow({
          title: 'Chat',
          type: 'chat',
          content: <ChatApp />,
          position: { x: 100, y: 100 },
          size: { width: 800, height: 600 },
        });
      },
    },
    {
      id: 'npcs',
      label: 'NPCs',
      emoji: '👥',
      action: () => {
        openWindow({
          title: 'NPC Directory',
          type: 'npc-list',
          content: (
            <div>
              <h2>Available NPCs</h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '16px' }}>
                {npcs.map((npc) => (
                  <div
                    key={npc.id}
                    style={{
                      padding: '12px',
                      background: 'var(--bg-tertiary)',
                      borderRadius: '8px',
                      border: '1px solid var(--border-color)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <div style={{ fontSize: '32px' }}>{npc.avatar}</div>
                      <div>
                        <div style={{ fontWeight: 600 }}>{npc.name}</div>
                        <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                          {npc.occupation} • {npc.location}
                        </div>
                        <div style={{ fontSize: '12px', marginTop: '4px' }}>
                          {npc.background}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ),
          position: { x: 150, y: 150 },
          size: { width: 600, height: 500 },
        });
      },
    },
    {
      id: 'about',
      label: 'About',
      emoji: 'ℹ️',
      action: () => {
        openWindow({
          title: 'About Recursive://Neon',
          type: 'about',
          content: (
            <div style={{ maxWidth: '500px' }}>
              <h2 style={{ marginBottom: '16px', color: 'var(--accent-cyan)' }}>
                Recursive://Neon
              </h2>
              <p style={{ marginBottom: '12px', lineHeight: '1.6' }}>
                A futuristic RPG with LLM-powered NPCs that create dynamic, engaging conversations.
              </p>
              <p style={{ marginBottom: '12px', lineHeight: '1.6' }}>
                Navigate this digital world through a desktop-like interface, interact with unique NPCs,
                and uncover the mysteries of the Recursive system.
              </p>
              <h3 style={{ marginTop: '24px', marginBottom: '12px', color: 'var(--accent-magenta)' }}>
                Technology
              </h3>
              <ul style={{ lineHeight: '1.8', paddingLeft: '20px' }}>
                <li>Frontend: React + TypeScript</li>
                <li>Backend: Python + FastAPI</li>
                <li>LLM: Ollama (local inference)</li>
                <li>NPCs: LangChain agents</li>
              </ul>
            </div>
          ),
          position: { x: 200, y: 200 },
          size: { width: 600, height: 400 },
        });
      },
    },
  ];

  return (
    <div className="desktop">
      {/* Desktop icons */}
      <div className="desktop-icons">
        {icons.map((icon) => (
          <div
            key={icon.id}
            className="desktop-icon"
            onClick={icon.action}
            onDoubleClick={icon.action}
          >
            <div className="desktop-icon-emoji">{icon.emoji}</div>
            <div className="desktop-icon-label">{icon.label}</div>
          </div>
        ))}
      </div>

      {/* Open windows */}
      {windows.map((window) => (
        <Window key={window.id} window={window} />
      ))}

      {/* Taskbar */}
      <Taskbar />
    </div>
  );
}
