/**
 * Hook for managing notification WebSocket handlers
 *
 * Registers and manages notification-related WebSocket message handlers.
 * Extracted from App.tsx for better testability and maintainability.
 */

import { useEffect } from 'react';
import { useWebSocket } from '../contexts/WebSocketContext';
import { useNotificationStore } from '../stores/notificationStore';

export function useNotificationHandlers(): void {
  const wsClient = useWebSocket();
  const {
    handleNotificationCreated,
    handleNotificationUpdated,
    handleNotificationDeleted,
    handleNotificationsCleared,
    handleConfigUpdated,
  } = useNotificationStore();

  useEffect(() => {
    // Notification event handlers
    const onNotificationCreated = (msg: any) => {
      handleNotificationCreated(msg.data);
    };

    const onNotificationUpdated = (msg: any) => {
      handleNotificationUpdated(msg.data);
    };

    const onNotificationDeleted = (msg: any) => {
      handleNotificationDeleted(msg.data.id);
    };

    const onNotificationsCleared = (_msg: any) => {
      handleNotificationsCleared();
    };

    const onNotificationConfigUpdated = (msg: any) => {
      handleConfigUpdated(msg.data);
    };

    // Register handlers
    wsClient.on('notification_created', onNotificationCreated);
    wsClient.on('notification_updated', onNotificationUpdated);
    wsClient.on('notification_deleted', onNotificationDeleted);
    wsClient.on('notifications_cleared', onNotificationsCleared);
    wsClient.on('notification_config_updated', onNotificationConfigUpdated);

    // Cleanup: remove all handlers on unmount
    return () => {
      wsClient.off('notification_created', onNotificationCreated);
      wsClient.off('notification_updated', onNotificationUpdated);
      wsClient.off('notification_deleted', onNotificationDeleted);
      wsClient.off('notifications_cleared', onNotificationsCleared);
      wsClient.off('notification_config_updated', onNotificationConfigUpdated);
    };
  }, [
    wsClient,
    handleNotificationCreated,
    handleNotificationUpdated,
    handleNotificationDeleted,
    handleNotificationsCleared,
    handleConfigUpdated,
  ]);
}
