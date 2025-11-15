/**
 * NotificationIndicator Component
 *
 * Displays a notification bell icon with unread count badge in the taskbar.
 * Clicking the indicator opens the Notification Center app.
 */

import { useNotificationStore } from '../../stores/notificationStore';
import { useGameStore } from '../../stores/gameStore';
import { NotificationCenterApp } from '../apps/NotificationCenterApp';

export function NotificationIndicator() {
  const { unreadCount } = useNotificationStore();
  const { openWindow } = useGameStore();

  const handleClick = () => {
    openWindow({
      title: 'Notifications',
      type: 'notification-center',
      content: <NotificationCenterApp />,
      size: { width: 600, height: 500 },
      position: { x: 100, y: 100 },
    });
  };

  return (
    <button
      className="notification-indicator"
      onClick={handleClick}
      aria-label={`Notifications (${unreadCount} unread)`}
    >
      <span className="notification-bell">🔔</span>
      {unreadCount > 0 && (
        <span className="notification-badge">{unreadCount}</span>
      )}
    </button>
  );
}
