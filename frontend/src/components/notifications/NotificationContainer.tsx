/**
 * NotificationContainer Component
 *
 * Container component that displays a stack of active toast notifications.
 * Manages positioning and layout based on configuration.
 */

import { useNotificationStore } from '../../stores/notificationStore';
import { NotificationToast } from './NotificationToast';

export function NotificationContainer() {
  const { activeNotifications, config, dismissNotification, markAsRead } =
    useNotificationStore();

  const getPositionClass = () => {
    return `notification-container-${config.position}`;
  };

  return (
    <div className={`notification-container ${getPositionClass()}`}>
      {activeNotifications.map(notification => (
        <NotificationToast
          key={notification.id}
          notification={notification}
          duration={config.defaultDuration}
          onDismiss={dismissNotification}
          onRead={markAsRead}
        />
      ))}
    </div>
  );
}
