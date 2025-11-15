/**
 * NotificationDemo App
 *
 * Demonstration app for testing and showcasing the notification system.
 * This app provides a UI for creating notifications with different types,
 * testing configuration changes, and viewing notification behavior.
 *
 * This is intended as a developer tool and example of how to use notifications.
 */

import { useState } from 'react';
import {
  useNotificationStore,
  NotificationType,
} from '../../stores/notificationStore';

export function NotificationDemoApp() {
  const { createNotification, updateConfig, config } = useNotificationStore();

  const [title, setTitle] = useState('');
  const [message, setMessage] = useState('');
  const [type, setType] = useState<NotificationType>(NotificationType.INFO);
  const [duration, setDuration] = useState(5000);

  const handleCreateNotification = async () => {
    if (!title.trim()) {
      alert('Please enter a title');
      return;
    }

    try {
      await createNotification({
        title: title.trim(),
        message: message.trim() || undefined,
        type,
        source: 'notification-demo',
        duration,
      });

      // Clear form after successful creation
      setTitle('');
      setMessage('');
    } catch (error) {
      console.error('Failed to create notification:', error);
      alert('Failed to create notification');
    }
  };

  const createExampleNotifications = async () => {
    const examples = [
      {
        title: 'Welcome!',
        message: 'This is an info notification',
        type: NotificationType.INFO,
      },
      {
        title: 'Success!',
        message: 'Operation completed successfully',
        type: NotificationType.SUCCESS,
      },
      {
        title: 'Warning',
        message: 'Please review your settings',
        type: NotificationType.WARNING,
      },
      {
        title: 'Error',
        message: 'Something went wrong',
        type: NotificationType.ERROR,
      },
    ];

    for (const example of examples) {
      await createNotification({
        ...example,
        source: 'notification-demo',
      });

      // Small delay between notifications
      await new Promise(resolve => setTimeout(resolve, 500));
    }
  };

  const handlePositionChange = async (
    position: typeof config.position
  ) => {
    await updateConfig({ position });
  };

  const handleDurationChange = async (defaultDuration: number) => {
    await updateConfig({ defaultDuration });
  };

  const handleMaxVisibleChange = async (maxVisible: number) => {
    await updateConfig({ maxVisible });
  };

  return (
    <div style={{ padding: '20px', height: '100%', overflow: 'auto' }}>
      <h2 style={{ marginBottom: '20px', color: 'var(--accent-cyan)' }}>
        Notification System Demo
      </h2>

      {/* Quick Examples */}
      <section style={{ marginBottom: '30px' }}>
        <h3 style={{ marginBottom: '12px' }}>Quick Examples</h3>
        <button
          onClick={createExampleNotifications}
          style={{
            padding: '10px 20px',
            background: 'var(--accent-cyan)',
            color: 'var(--bg-primary)',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontWeight: '600',
          }}
        >
          Create All Example Notifications
        </button>
      </section>

      {/* Create Custom Notification */}
      <section style={{ marginBottom: '30px' }}>
        <h3 style={{ marginBottom: '12px' }}>Create Custom Notification</h3>

        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            background: 'var(--bg-secondary)',
            padding: '16px',
            borderRadius: '8px',
          }}
        >
          <div>
            <label style={{ display: 'block', marginBottom: '6px', fontSize: '14px' }}>
              Title *
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Notification title"
              style={{
                width: '100%',
                padding: '8px',
                background: 'var(--bg-primary)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-color)',
                borderRadius: '4px',
                fontSize: '14px',
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '6px', fontSize: '14px' }}>
              Message (optional)
            </label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Notification message"
              rows={3}
              style={{
                width: '100%',
                padding: '8px',
                background: 'var(--bg-primary)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-color)',
                borderRadius: '4px',
                fontSize: '14px',
                resize: 'vertical',
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '6px', fontSize: '14px' }}>
              Type
            </label>
            <select
              value={type}
              onChange={(e) => setType(e.target.value as NotificationType)}
              style={{
                width: '100%',
                padding: '8px',
                background: 'var(--bg-primary)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-color)',
                borderRadius: '4px',
                fontSize: '14px',
              }}
            >
              <option value={NotificationType.INFO}>Info</option>
              <option value={NotificationType.SUCCESS}>Success</option>
              <option value={NotificationType.WARNING}>Warning</option>
              <option value={NotificationType.ERROR}>Error</option>
            </select>
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '6px', fontSize: '14px' }}>
              Duration (ms)
            </label>
            <input
              type="number"
              value={duration}
              onChange={(e) => setDuration(parseInt(e.target.value))}
              min="0"
              step="1000"
              style={{
                width: '100%',
                padding: '8px',
                background: 'var(--bg-primary)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-color)',
                borderRadius: '4px',
                fontSize: '14px',
              }}
            />
            <small style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
              Set to 0 for no auto-dismiss
            </small>
          </div>

          <button
            onClick={handleCreateNotification}
            style={{
              padding: '10px 20px',
              background: 'var(--accent-blue)',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontWeight: '600',
              marginTop: '8px',
            }}
          >
            Create Notification
          </button>
        </div>
      </section>

      {/* Configuration */}
      <section style={{ marginBottom: '30px' }}>
        <h3 style={{ marginBottom: '12px' }}>Configuration</h3>

        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
            background: 'var(--bg-secondary)',
            padding: '16px',
            borderRadius: '8px',
          }}
        >
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px' }}>
              Position
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px' }}>
              {[
                ['top-left', 'Top Left'],
                ['top-center', 'Top Center'],
                ['top-right', 'Top Right'],
                ['bottom-left', 'Bottom Left'],
                ['bottom-center', 'Bottom Center'],
                ['bottom-right', 'Bottom Right'],
              ].map(([value, label]) => (
                <button
                  key={value}
                  onClick={() => handlePositionChange(value as any)}
                  style={{
                    padding: '8px',
                    background: config.position === value ? 'var(--accent-cyan)' : 'var(--bg-tertiary)',
                    color: config.position === value ? 'var(--bg-primary)' : 'var(--text-primary)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '12px',
                    fontWeight: config.position === value ? '600' : '400',
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px' }}>
              Default Duration: {config.defaultDuration}ms
            </label>
            <input
              type="range"
              min="1000"
              max="10000"
              step="1000"
              value={config.defaultDuration}
              onChange={(e) => handleDurationChange(parseInt(e.target.value))}
              style={{ width: '100%' }}
            />
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px' }}>
              Max Visible: {config.maxVisible}
            </label>
            <input
              type="range"
              min="1"
              max="10"
              step="1"
              value={config.maxVisible}
              onChange={(e) => handleMaxVisibleChange(parseInt(e.target.value))}
              style={{ width: '100%' }}
            />
          </div>
        </div>
      </section>

      {/* Usage Guide */}
      <section>
        <h3 style={{ marginBottom: '12px' }}>Usage Example</h3>
        <pre
          style={{
            background: 'var(--bg-secondary)',
            padding: '16px',
            borderRadius: '8px',
            fontSize: '12px',
            overflow: 'auto',
            color: 'var(--text-secondary)',
          }}
        >
          {`import { useNotificationStore, NotificationType } from './stores/notificationStore';

function MyApp() {
  const { createNotification } = useNotificationStore();

  const handleAction = async () => {
    try {
      // Perform action...

      await createNotification({
        title: 'Action Successful',
        message: 'Your changes have been saved',
        type: NotificationType.SUCCESS,
        source: 'my-app',
      });
    } catch (error) {
      await createNotification({
        title: 'Action Failed',
        message: error.message,
        type: NotificationType.ERROR,
        source: 'my-app',
      });
    }
  };

  return <button onClick={handleAction}>Perform Action</button>;
}`}
        </pre>
      </section>
    </div>
  );
}
