/**
 * Taskbar component - Bottom taskbar with open windows and status
 */

import { useGameStore } from '../stores/gameStore';

export function Taskbar() {
  const { windows, restoreWindow, systemStatus, connected } = useGameStore();

  return (
    <div className="taskbar">
      <div className="taskbar-start">
        <div className="taskbar-logo">Recursive://Neon</div>
      </div>

      <div className="taskbar-items">
        {windows.map((window) => (
          <div
            key={window.id}
            className={`taskbar-item ${!window.minimized ? 'active' : ''}`}
            onClick={() => {
              if (window.minimized) {
                restoreWindow(window.id);
              }
            }}
          >
            {window.title}
          </div>
        ))}
      </div>

      <div className="taskbar-status">
        <div className="status-indicator">
          <span className={`status-dot ${connected ? '' : 'disconnected'}`} />
          <span>{connected ? 'Connected' : 'Disconnected'}</span>
        </div>
        {systemStatus && (
          <div className="status-indicator">
            <span>NPCs: {systemStatus.system.npcs_loaded}</span>
          </div>
        )}
      </div>
    </div>
  );
}
