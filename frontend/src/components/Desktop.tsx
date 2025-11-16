/**
 * Desktop component - Main desktop environment
 */

import { useGameStore } from '../stores/gameStore';
import { Window } from './Window';
import { Taskbar } from './Taskbar';
import { ErrorBoundary } from './ErrorBoundary';
import { ChatApp } from './apps/ChatApp';
import { NotesApp } from './apps/NotesApp';
import { TaskListApp } from './apps/TaskListApp';
import { FileBrowserApp } from './apps/FileBrowserApp';
import { TextEditorApp } from './apps/TextEditorApp';
import { ImageViewerApp } from './apps/ImageViewerApp';
import { WebBrowserApp } from './apps/WebBrowserApp';
import { TerminalApp } from './apps/TerminalApp';
import { CalendarApp } from './apps/CalendarApp';
import { NotificationContainer } from './notifications/NotificationContainer';
import { NotificationDemoApp } from './apps/NotificationDemoApp';
import { ClockWidget } from './ClockWidget';
import { SettingsApp } from './apps/SettingsApp';
import { MediaViewerApp } from './apps/MediaViewerApp';
import { PortScannerApp } from './apps/minigames/PortScannerApp';
import { CircuitBreakerApp } from './apps/minigames/CircuitBreakerApp';
import { MinigameErrorBoundary } from './apps/minigames/MinigameErrorBoundary';

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
          minimized: false,
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
          minimized: false,
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
          minimized: false,
        });
      },
    },
    {
      id: 'notes',
      label: 'Notes',
      emoji: '📝',
      action: () => {
        openWindow({
          title: 'Notes',
          type: 'notes',
          content: <NotesApp />,
          position: { x: 120, y: 120 },
          size: { width: 900, height: 600 },
          minimized: false,
        });
      },
    },
    {
      id: 'tasks',
      label: 'Tasks',
      emoji: '✅',
      action: () => {
        openWindow({
          title: 'Task Lists',
          type: 'tasks',
          content: <TaskListApp />,
          position: { x: 140, y: 140 },
          size: { width: 800, height: 600 },
          minimized: false,
        });
      },
    },
    {
      id: 'calendar',
      label: 'Calendar',
      emoji: '📅',
      action: () => {
        openWindow({
          title: 'Calendar',
          type: 'calendar',
          content: (
            <ErrorBoundary>
              <CalendarApp />
            </ErrorBoundary>
          ),
          position: { x: 150, y: 150 },
          size: { width: 1000, height: 700 },
          minimized: false,
        });
      },
    },
    {
      id: 'files',
      label: 'Files',
      emoji: '📁',
      action: () => {
        openWindow({
          title: 'File Browser',
          type: 'files',
          content: <FileBrowserApp />,
          position: { x: 160, y: 160 },
          size: { width: 800, height: 600 },
          minimized: false,
        });
      },
    },
    {
      id: 'editor',
      label: 'Text Editor',
      emoji: '📄',
      action: () => {
        openWindow({
          title: 'Text Editor',
          type: 'editor',
          content: <TextEditorApp />,
          position: { x: 180, y: 180 },
          size: { width: 900, height: 700 },
          minimized: false,
        });
      },
    },
    {
      id: 'images',
      label: 'Images',
      emoji: '🖼️',
      action: () => {
        openWindow({
          title: 'Image Viewer',
          type: 'images',
          content: <ImageViewerApp />,
          position: { x: 200, y: 200 },
          size: { width: 800, height: 600 },
          minimized: false,
        });
      },
    },
    {
      id: 'browser',
      label: 'Browser',
      emoji: '🌐',
      action: () => {
        openWindow({
          title: 'Web Browser',
          type: 'browser',
          content: <WebBrowserApp />,
          position: { x: 220, y: 220 },
          size: { width: 1000, height: 700 },
          minimized: false,
        });
      },
    },
    {
      id: 'terminal',
      label: 'Terminal',
      emoji: '⌨️',
      action: () => {
        openWindow({
          title: 'Terminal',
          type: 'terminal',
          content: <TerminalApp />,
          position: { x: 240, y: 240 },
          size: { width: 900, height: 650 },
          minimized: false,
        });
      },
    },
    {
      id: 'portscanner',
      label: 'PortScanner',
      emoji: '🔍',
      action: () => {
        openWindow({
          title: 'PortScanner',
          type: 'portscanner',
          content: (
            <MinigameErrorBoundary gameName="PortScanner">
              <PortScannerApp />
            </MinigameErrorBoundary>
          ),
          position: { x: 250, y: 250 },
          size: { width: 700, height: 700 },
          minimized: false,
        });
      },
    },
    {
      id: 'circuitbreaker',
      label: 'CircuitBreaker',
      emoji: '⚡',
      action: () => {
        openWindow({
          title: 'CircuitBreaker',
          type: 'circuitbreaker',
          content: (
            <MinigameErrorBoundary gameName="CircuitBreaker">
              <CircuitBreakerApp />
            </MinigameErrorBoundary>
          ),
          position: { x: 270, y: 270 },
          size: { width: 700, height: 750 },
          minimized: false,
        });
      },
    },
    {
      id: 'notification-demo',
      label: 'Notifications',
      emoji: '🔔',
      action: () => {
        openWindow({
          title: 'Notification Demo',
          type: 'notification-demo',
          content: <NotificationDemoApp />,
          position: { x: 260, y: 260 },
          size: { width: 600, height: 650 },
          minimized: false,
        });
      },
    },
    {
      id: 'settings',
      label: 'Settings',
      emoji: '⚙️',
      action: () => {
        openWindow({
          title: 'Settings',
          type: 'settings',
          content: <SettingsApp />,
          position: { x: 280, y: 280 },
          size: { width: 900, height: 600 },
          minimized: false,
        });
      },
    },
    {
      id: 'media-viewer',
      label: 'MindSync',
      emoji: '🌀',
      action: () => {
        openWindow({
          title: 'MindSync Wellness',
          type: 'media-viewer',
          content: <MediaViewerApp />,
          position: { x: 100, y: 80 },
          size: { width: 900, height: 750 },
          minimized: false,
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

      {/* Notification toasts */}
      <NotificationContainer />

      {/* Clock widget */}
      <ClockWidget />

      {/* Taskbar */}
      <Taskbar />
    </div>
  );
}
