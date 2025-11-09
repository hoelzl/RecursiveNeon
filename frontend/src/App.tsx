/**
 * Main App component
 */

import { useEffect, useState } from 'react';
import { Desktop } from './components/Desktop';
import { useGameStore } from './stores/gameStore';
import { wsClient } from './services/websocket';
import './styles/desktop.css';

function App() {
  const { setNPCs, setSystemStatus, setConnected } = useGameStore();
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
      wsClient.disconnect();
    };
  }, [setNPCs, setSystemStatus, setConnected]);

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
