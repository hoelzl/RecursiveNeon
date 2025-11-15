/**
 * Main App component
 *
 * Refactored for testability using dependency injection through React Context.
 * Dependencies are injected via context providers instead of direct imports.
 */

import { useEffect, useState } from 'react';
import { Desktop } from './components/Desktop';
import { useGameStoreContext } from './contexts/GameStoreContext';
import { useWebSocket } from './contexts/WebSocketContext';
import { useNotificationStore } from './stores/notificationStore';
import { timeService } from './services/timeService';
import { settingsService } from './services/settingsService';
import './styles/desktop.css';

function App() {
  const { setNPCs, setSystemStatus, setConnected } = useGameStoreContext();
  const wsClient = useWebSocket();
  const {
    handleNotificationCreated,
    handleNotificationUpdated,
    handleNotificationDeleted,
    handleNotificationsCleared,
    handleConfigUpdated,
    loadHistory,
    loadConfig,
  } = useNotificationStore();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    const initialize = async () => {
      try {
        // Connect to WebSocket
        await wsClient.connect();

        if (!mounted) return;
        setConnected(true);

        // Request initial data
        wsClient.send('get_npcs', {});
        wsClient.send('get_status', {});

        // Load notification data
        loadHistory();
        loadConfig();

        // Initialize time and settings services
        timeService.initialize(wsClient);
        settingsService.initialize(wsClient);

        // Set up message handlers
        wsClient.on('npcs_list', (msg) => {
          if (mounted) {
            setNPCs(msg.data.npcs);
          }
        });

        wsClient.on('status', (msg) => {
          if (mounted) {
            setSystemStatus(msg.data);
          }
        });

        wsClient.on('error', (msg) => {
          console.error('Server error:', msg.data);
        });

        // Notification event handlers
        wsClient.on('notification_created', (msg) => {
          if (mounted) {
            handleNotificationCreated(msg.data);
          }
        });

        wsClient.on('notification_updated', (msg) => {
          if (mounted) {
            handleNotificationUpdated(msg.data);
          }
        });

        wsClient.on('notification_deleted', (msg) => {
          if (mounted) {
            handleNotificationDeleted(msg.data.id);
          }
        });

        wsClient.on('notifications_cleared', (msg) => {
          if (mounted) {
            handleNotificationsCleared();
          }
        });

        wsClient.on('notification_config_updated', (msg) => {
          if (mounted) {
            handleConfigUpdated(msg.data);
          }
        });

        // Time service event handlers
        wsClient.on('time_response', (msg) => {
          if (mounted) {
            timeService.handleTimeUpdate(msg);
          }
        });

        wsClient.on('time_update', (msg) => {
          if (mounted) {
            timeService.handleTimeUpdate(msg);
          }
        });

        // Settings service event handlers
        wsClient.on('settings_response', (msg) => {
          if (mounted) {
            settingsService.handleSettingsResponse(msg);
          }
        });

        wsClient.on('setting_update', (msg) => {
          if (mounted) {
            settingsService.handleSettingUpdate(msg);
          }
        });

        wsClient.on('settings_update', (msg) => {
          if (mounted) {
            settingsService.handleSettingsUpdate(msg);
          }
        });

        setLoading(false);
      } catch (err) {
        console.error('Failed to initialize:', err);
        if (mounted) {
          setError('Failed to connect to server. Please ensure the backend is running.');
          setLoading(false);
        }
      }
    };

    initialize();

    return () => {
      mounted = false;
      timeService.destroy();
      wsClient.disconnect();
    };
  }, [setNPCs, setSystemStatus, setConnected, handleNotificationCreated, handleNotificationUpdated, handleNotificationDeleted, handleNotificationsCleared, handleConfigUpdated, loadHistory, loadConfig]);

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
          onClick={() => window.location.reload()}
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

  return <Desktop />;
}

export default App;
