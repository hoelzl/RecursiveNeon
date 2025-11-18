/**
 * Main App component
 *
 * Refactored for improved maintainability and testability.
 * Uses custom hooks to separate concerns and eliminate complexity.
 */

import { useEffect } from 'react';
import { Desktop } from './components/Desktop';
import { useAppInitialization } from './hooks/useAppInitialization';
import { useWebSocketHandlers } from './hooks/useWebSocketHandlers';
import { useNotificationHandlers } from './hooks/useNotificationHandlers';
import { timeService } from './services/timeService';
import './styles/desktop.css';

function App() {
  // Initialize the application (WebSocket connection, initial data)
  const { loading, error, retryConnection } = useAppInitialization();

  // Set up WebSocket event handlers for NPCs, status, time, settings
  useWebSocketHandlers();

  // Set up notification-specific WebSocket handlers
  useNotificationHandlers();

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      timeService.destroy();
    };
  }, []);

  // Loading state
  if (loading) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        background: 'var(--bg-primary)',
        color: 'var(--text-primary)',
        gap: '16px',
      }}>
        <div style={{ fontSize: '48px' }}>⚡</div>
        <div style={{ fontSize: '24px', fontWeight: 600 }}>Recursive://Neon</div>
        <div style={{ color: 'var(--text-secondary)' }}>Initializing...</div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        background: 'var(--bg-primary)',
        color: 'var(--text-primary)',
        gap: '16px',
        padding: '32px',
      }}>
        <div style={{ fontSize: '48px' }}>❌</div>
        <div style={{ fontSize: '24px', fontWeight: 600 }}>Connection Error</div>
        <div style={{ color: 'var(--text-secondary)', textAlign: 'center', maxWidth: '500px' }}>
          {error}
        </div>
        <button
          onClick={retryConnection}
          style={{
            marginTop: '16px',
            padding: '12px 24px',
            background: 'var(--accent-cyan)',
            border: 'none',
            borderRadius: '4px',
            color: 'var(--bg-primary)',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  // Main application
  return <Desktop />;
}

export default App;
