/**
 * NotificationToast Component
 *
 * Individual toast notification component that displays temporarily on the desktop.
 * Features:
 * - Auto-dismiss after configurable duration
 * - Manual dismiss with close button
 * - Pause auto-dismiss on hover
 * - Smooth slide + fade animations
 * - Type-based styling (info, success, warning, error)
 */

import { useEffect, useState } from 'react';
import type { Notification, NotificationType } from '../../stores/notificationStore';

interface NotificationToastProps {
  notification: Notification;
  duration?: number;
  onDismiss: (id: string) => void;
  onRead: (id: string) => void;
}

export function NotificationToast({
  notification,
  duration = 5000,
  onDismiss,
  onRead,
}: NotificationToastProps) {
  const [isPaused, setIsPaused] = useState(false);
  const [isExiting, setIsExiting] = useState(false);

  // Auto-dismiss timer
  useEffect(() => {
    // Don't start timer if duration is 0 (no auto-dismiss) or paused
    if (duration === 0 || isPaused) return;

    const timer = setTimeout(() => {
      handleDismiss();
    }, duration);

    return () => clearTimeout(timer);
  }, [duration, isPaused]);

  const handleDismiss = () => {
    setIsExiting(true);

    // Wait for exit animation before removing
    setTimeout(() => {
      onDismiss(notification.id);

      // Mark as read if not already
      if (!notification.read) {
        onRead(notification.id);
      }
    }, 200); // Match exit animation duration
  };

  const getIcon = (type: NotificationType): string => {
    const icons = {
      info: 'ℹ️',
      success: '✅',
      warning: '⚠️',
      error: '❌',
    };
    return icons[type];
  };

  const formatTime = (timestamp: string): string => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div
      className={`notification-toast notification-toast-${notification.type} ${
        isExiting ? 'exiting' : ''
      }`}
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
    >
      <div className="notification-toast-icon">
        {getIcon(notification.type)}
      </div>

      <div className="notification-toast-content">
        <div className="notification-toast-title">{notification.title}</div>

        {notification.message && (
          <div className="notification-toast-message">{notification.message}</div>
        )}

        <div className="notification-toast-time">
          {formatTime(notification.createdAt)}
        </div>
      </div>

      <button
        className="notification-toast-close"
        onClick={handleDismiss}
        aria-label="Dismiss notification"
      >
        ×
      </button>
    </div>
  );
}
