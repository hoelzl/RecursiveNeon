/**
 * Notification Store
 *
 * Zustand store for managing notifications in the RecursiveNeon desktop.
 * Handles notification state, API interactions, and WebSocket updates.
 */

import { create } from 'zustand';

// ============================================================================
// Types
// ============================================================================

export enum NotificationType {
  INFO = 'info',
  SUCCESS = 'success',
  WARNING = 'warning',
  ERROR = 'error',
}

export interface Notification {
  id: string;
  title: string;
  message?: string;
  type: NotificationType;
  source: string;
  createdAt: string;
  read: boolean;
  dismissed: boolean;
}

export interface NotificationConfig {
  position: 'top-left' | 'top-right' | 'top-center' |
           'bottom-left' | 'bottom-right' | 'bottom-center';
  defaultDuration: number;
  maxVisible: number;
  soundEnabled: boolean;
}

export interface NotificationOptions {
  title: string;
  message?: string;
  type?: NotificationType;
  duration?: number;
  source?: string;
}

// ============================================================================
// Store Interface
// ============================================================================

interface NotificationState {
  // State
  activeNotifications: Notification[];
  history: Notification[];
  unreadCount: number;
  config: NotificationConfig;

  // Actions
  createNotification: (options: NotificationOptions) => Promise<void>;
  dismissNotification: (id: string) => void;
  markAsRead: (id: string) => Promise<void>;
  markAllAsRead: () => Promise<void>;
  deleteNotification: (id: string) => Promise<void>;
  clearAll: () => Promise<void>;
  loadHistory: () => Promise<void>;
  loadConfig: () => Promise<void>;
  updateConfig: (config: Partial<NotificationConfig>) => Promise<void>;

  // WebSocket handlers
  handleNotificationCreated: (notification: Notification) => void;
  handleNotificationUpdated: (notification: Notification) => void;
  handleNotificationDeleted: (id: string) => void;
  handleNotificationsCleared: () => void;
  handleConfigUpdated: (config: NotificationConfig) => void;
}

// ============================================================================
// API Helper Functions
// ============================================================================

const API_BASE = 'http://localhost:8000/api/notifications';

async function apiRequest<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.statusText}`);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return null as T;
  }

  return response.json();
}

// ============================================================================
// Store Implementation
// ============================================================================

export const useNotificationStore = create<NotificationState>((set, get) => ({
  // ========================================================================
  // Initial State
  // ========================================================================

  activeNotifications: [],
  history: [],
  unreadCount: 0,
  config: {
    position: 'top-right',
    defaultDuration: 5000,
    maxVisible: 5,
    soundEnabled: false,
  },

  // ========================================================================
  // Actions
  // ========================================================================

  /**
   * Create a new notification
   */
  createNotification: async (options: NotificationOptions) => {
    await apiRequest('', {
      method: 'POST',
      body: JSON.stringify({
        title: options.title,
        message: options.message,
        type: options.type || NotificationType.INFO,
        source: options.source || 'system',
      }),
    });

    // Notification will be added via WebSocket event
  },

  /**
   * Dismiss notification (remove from active display)
   * Note: This is a local-only action, doesn't hit the API
   */
  dismissNotification: (id: string) => {
    set(state => ({
      activeNotifications: state.activeNotifications.filter(n => n.id !== id),
    }));
  },

  /**
   * Mark notification as read
   */
  markAsRead: async (id: string) => {
    await apiRequest(`/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ read: true }),
    });

    // Update will be handled via WebSocket event
  },

  /**
   * Mark all notifications as read
   */
  markAllAsRead: async () => {
    const { history } = get();
    const unreadIds = history.filter(n => !n.read).map(n => n.id);

    // Mark each unread notification as read
    await Promise.all(
      unreadIds.map(id => get().markAsRead(id))
    );
  },

  /**
   * Delete a notification
   */
  deleteNotification: async (id: string) => {
    await apiRequest(`/${id}`, {
      method: 'DELETE',
    });

    // Deletion will be handled via WebSocket event
  },

  /**
   * Clear all notifications
   */
  clearAll: async () => {
    await apiRequest('', {
      method: 'DELETE',
    });

    // Clear will be handled via WebSocket event
  },

  /**
   * Load notification history from API
   */
  loadHistory: async () => {
    const notifications = await apiRequest<Notification[]>('');
    const unreadCount = notifications.filter((n: Notification) => !n.read).length;

    set({ history: notifications, unreadCount });
  },

  /**
   * Load notification configuration from API
   */
  loadConfig: async () => {
    const config = await apiRequest<NotificationConfig>('/config');
    set({ config });
  },

  /**
   * Update notification configuration
   */
  updateConfig: async (newConfig: Partial<NotificationConfig>) => {
    const { config } = get();
    const updatedConfig = { ...config, ...newConfig };

    await apiRequest('/config', {
      method: 'PUT',
      body: JSON.stringify(updatedConfig),
    });

    // Config will be updated via WebSocket event
  },

  // ========================================================================
  // WebSocket Event Handlers
  // ========================================================================

  /**
   * Handle notification_created event from WebSocket
   */
  handleNotificationCreated: (notification: Notification) => {
    set(state => {
      // Check if notification already exists (deduplicate)
      const existsInHistory = state.history.some(n => n.id === notification.id);
      const existsInActive = state.activeNotifications.some(n => n.id === notification.id);

      // If already exists, don't add duplicate
      if (existsInHistory || existsInActive) {
        console.warn(`Duplicate notification received: ${notification.id}`);
        return state; // No changes
      }

      const newHistory = [notification, ...state.history];
      const newUnreadCount = state.unreadCount + 1;

      // Add to active notifications
      let newActive = [...state.activeNotifications, notification];

      // Respect maxVisible limit
      if (newActive.length > state.config.maxVisible) {
        newActive = newActive.slice(-state.config.maxVisible);
      }

      return {
        activeNotifications: newActive,
        history: newHistory,
        unreadCount: newUnreadCount,
      };
    });
  },

  /**
   * Handle notification_updated event from WebSocket
   */
  handleNotificationUpdated: (notification: Notification) => {
    set(state => {
      // Update in history
      const updatedHistory = state.history.map(n =>
        n.id === notification.id ? notification : n
      );

      // Recalculate unread count
      const newUnreadCount = updatedHistory.filter(n => !n.read).length;

      // Update in active notifications if present
      const updatedActive = state.activeNotifications.map(n =>
        n.id === notification.id ? notification : n
      );

      return {
        history: updatedHistory,
        unreadCount: newUnreadCount,
        activeNotifications: updatedActive,
      };
    });
  },

  /**
   * Handle notification_deleted event from WebSocket
   */
  handleNotificationDeleted: (id: string) => {
    set(state => {
      const updatedHistory = state.history.filter(n => n.id !== id);
      const newUnreadCount = updatedHistory.filter(n => !n.read).length;

      return {
        activeNotifications: state.activeNotifications.filter(n => n.id !== id),
        history: updatedHistory,
        unreadCount: newUnreadCount,
      };
    });
  },

  /**
   * Handle notifications_cleared event from WebSocket
   */
  handleNotificationsCleared: () => {
    set({
      activeNotifications: [],
      history: [],
      unreadCount: 0,
    });
  },

  /**
   * Handle notification_config_updated event from WebSocket
   */
  handleConfigUpdated: (config: NotificationConfig) => {
    set({ config });
  },
}));
