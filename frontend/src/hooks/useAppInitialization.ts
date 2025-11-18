/**
 * Hook for managing app initialization
 *
 * Handles WebSocket connection, initial data requests, and loading/error states.
 * Extracted from App.tsx for better testability and maintainability.
 */

import { useState, useEffect } from 'react';
import { useGameStoreContext } from '../contexts/GameStoreContext';
import { useWebSocket } from '../contexts/WebSocketContext';
import { useNotificationStore } from '../stores/notificationStore';
import { timeService } from '../services/timeService';
import { settingsService } from '../services/settingsService';

export interface UseAppInitializationResult {
  loading: boolean;
  error: string | null;
  retryConnection: () => void;
}

export function useAppInitialization(): UseAppInitializationResult {
  const { setConnected } = useGameStoreContext();
  const wsClient = useWebSocket();
  const { loadHistory, loadConfig } = useNotificationStore();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const initialize = async () => {
    try {
      setLoading(true);
      setError(null);

      // Connect to WebSocket
      await wsClient.connect();

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

      setLoading(false);
    } catch (err) {
      console.error('Failed to initialize:', err);
      setError('Failed to connect to server. Please ensure the backend is running.');
      setLoading(false);
    }
  };

  useEffect(() => {
    initialize();

    // Cleanup: disconnect WebSocket on unmount
    return () => {
      wsClient.disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run on mount

  const retryConnection = () => {
    initialize();
  };

  return {
    loading,
    error,
    retryConnection,
  };
}
