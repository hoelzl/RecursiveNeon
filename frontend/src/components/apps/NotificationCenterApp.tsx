/**
 * NotificationCenter App
 *
 * Desktop application for viewing and managing notification history.
 * Features:
 * - View all notifications in reverse chronological order
 * - Filter by type (info, success, warning, error)
 * - Search notification content
 * - Mark as read/unread
 * - Delete notifications
 * - Clear all notifications
 */

import { useState, useEffect } from 'react';
import {
  useNotificationStore,
  NotificationType,
  type Notification,
} from '../../stores/notificationStore';

export function NotificationCenterApp() {
  const {
    history,
    unreadCount,
    markAsRead,
    markAllAsRead,
    deleteNotification,
    clearAll,
    loadHistory,
  } = useNotificationStore();

  const [filter, setFilter] = useState<'all' | NotificationType>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Load history when component mounts
  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  // Filter and search notifications
  const filteredNotifications = history.filter(notification => {
    // Apply type filter
    if (filter !== 'all' && notification.type !== filter) {
      return false;
    }

    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      const titleMatch = notification.title.toLowerCase().includes(query);
      const messageMatch = notification.message?.toLowerCase().includes(query);
      return titleMatch || messageMatch;
    }

    return true;
  });

  const handleNotificationClick = (notification: Notification) => {
    if (!notification.read) {
      markAsRead(notification.id);
    }
  };

  const handleClearAll = async () => {
    if (confirm('Are you sure you want to clear all notifications?')) {
      await clearAll();
    }
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

  const formatTimestamp = (timestamp: string): string => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString();
  };

  return (
    <div className="notification-center-app">
      {/* Header */}
      <div className="notification-center-header">
        <div className="notification-center-title">
          <h2>Notifications</h2>
          {unreadCount > 0 && (
            <span className="notification-center-unread-badge">
              {unreadCount} unread
            </span>
          )}
        </div>

        <div className="notification-center-actions">
          <button
            onClick={markAllAsRead}
            disabled={unreadCount === 0}
            className="btn-secondary"
          >
            Mark All Read
          </button>
          <button
            onClick={handleClearAll}
            disabled={history.length === 0}
            className="btn-danger"
          >
            Clear All
          </button>
        </div>
      </div>

      {/* Filters and Search */}
      <div className="notification-center-filters">
        <div className="filter-buttons">
          <button
            className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
            onClick={() => setFilter('all')}
          >
            All
          </button>
          <button
            className={`filter-btn ${filter === NotificationType.INFO ? 'active' : ''}`}
            onClick={() => setFilter(NotificationType.INFO)}
          >
            Info
          </button>
          <button
            className={`filter-btn ${filter === NotificationType.SUCCESS ? 'active' : ''}`}
            onClick={() => setFilter(NotificationType.SUCCESS)}
          >
            Success
          </button>
          <button
            className={`filter-btn ${filter === NotificationType.WARNING ? 'active' : ''}`}
            onClick={() => setFilter(NotificationType.WARNING)}
          >
            Warning
          </button>
          <button
            className={`filter-btn ${filter === NotificationType.ERROR ? 'active' : ''}`}
            onClick={() => setFilter(NotificationType.ERROR)}
          >
            Error
          </button>
        </div>

        <input
          type="text"
          placeholder="Search notifications..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="notification-search"
        />
      </div>

      {/* Notification List */}
      <div className="notification-center-list">
        {filteredNotifications.length === 0 ? (
          <div className="notification-center-empty">
            {searchQuery || filter !== 'all' ? (
              <p>No notifications match your filters</p>
            ) : (
              <p>No notifications yet</p>
            )}
          </div>
        ) : (
          filteredNotifications.map(notification => (
            <div
              key={notification.id}
              className={`notification-item notification-item-${notification.type} ${
                !notification.read ? 'unread' : ''
              }`}
              onClick={() => handleNotificationClick(notification)}
            >
              <div className="notification-item-header">
                <span className="notification-item-icon">
                  {getIcon(notification.type)}
                </span>

                <span
                  className={`notification-item-dot ${
                    !notification.read ? 'active' : ''
                  }`}
                >
                  {!notification.read && '●'}
                </span>

                <span className="notification-item-title">
                  {notification.title}
                </span>

                <span className="notification-item-time">
                  {formatTimestamp(notification.createdAt)}
                </span>

                <button
                  className="notification-item-delete"
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteNotification(notification.id);
                  }}
                  aria-label="Delete notification"
                >
                  🗑️
                </button>
              </div>

              {notification.message && (
                <div className="notification-item-message">
                  {notification.message}
                </div>
              )}

              <div className="notification-item-meta">
                <span className="notification-item-source">
                  Source: {notification.source}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
