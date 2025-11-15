# Notification System Developer Guide

> **Last Updated**: 2025-11-15
> **Project**: Recursive://Neon - LLM-Powered RPG
> **Purpose**: Developer guide for using the notification system

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Frontend Usage](#frontend-usage)
4. [Backend Usage](#backend-usage)
5. [API Reference](#api-reference)
6. [Examples](#examples)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The RecursiveNeon notification system provides a unified way for applications to display toast notifications and maintain notification history. The system consists of:

- **Toast Notifications**: Temporary, non-intrusive notifications displayed on screen
- **Notification Center**: Desktop app for viewing full notification history
- **Notification Indicator**: Taskbar badge showing unread count
- **Real-time Updates**: WebSocket integration for instant notification delivery

### Key Features

- ✅ Four notification types (info, success, warning, error)
- ✅ Auto-dismiss with configurable duration
- ✅ Pause on hover
- ✅ Persistent notification history
- ✅ Read/unread tracking
- ✅ Filter and search capabilities
- ✅ Configurable display position and behavior
- ✅ Real-time synchronization across clients

---

## Quick Start

### Creating Your First Notification (Frontend)

```typescript
import { useNotificationStore, NotificationType } from '../stores/notificationStore';

function MyApp() {
  const { createNotification } = useNotificationStore();

  const handleSuccess = async () => {
    await createNotification({
      title: 'Operation Complete',
      message: 'Your file has been saved successfully',
      type: NotificationType.SUCCESS,
      source: 'my-app',
    });
  };

  return (
    <button onClick={handleSuccess}>
      Save File
    </button>
  );
}
```

### Creating a Notification (Backend)

```python
from recursive_neon.models.notification import NotificationCreate, NotificationType

# In your endpoint or service
notification_data = NotificationCreate(
    title="Task Complete",
    message="Your backup has finished",
    type=NotificationType.SUCCESS,
    source="task-manager"
)

notification = container.notification_service.create_notification(notification_data)

# Notification will be broadcast via WebSocket automatically
```

---

## Frontend Usage

### Importing the Store

```typescript
import {
  useNotificationStore,
  NotificationType,
  type Notification,
  type NotificationOptions,
} from '../stores/notificationStore';
```

### Creating Notifications

#### Basic Notification

```typescript
const { createNotification } = useNotificationStore();

await createNotification({
  title: 'Hello World',
  source: 'my-app',
});
```

#### Full Options

```typescript
await createNotification({
  title: 'Data Synced',                    // Required
  message: 'All changes have been saved',  // Optional
  type: NotificationType.SUCCESS,          // Optional, default: INFO
  source: 'sync-service',                  // Optional, default: 'system'
  duration: 7000,                          // Optional (client-side only)
});
```

### Notification Types

```typescript
enum NotificationType {
  INFO = 'info',       // Blue - general information
  SUCCESS = 'success', // Green - successful operations
  WARNING = 'warning', // Orange - warnings/cautions
  ERROR = 'error',     // Red - errors/failures
}
```

### Managing Notifications

#### Mark as Read

```typescript
const { markAsRead } = useNotificationStore();

// Mark single notification as read
await markAsRead(notificationId);
```

#### Mark All as Read

```typescript
const { markAllAsRead } = useNotificationStore();

await markAllAsRead();
```

#### Delete Notification

```typescript
const { deleteNotification } = useNotificationStore();

await deleteNotification(notificationId);
```

#### Clear All Notifications

```typescript
const { clearAll } = useNotificationStore();

await clearAll();
```

### Accessing Notification History

```typescript
function MyComponent() {
  const { history, unreadCount, loadHistory } = useNotificationStore();

  useEffect(() => {
    loadHistory(); // Load from server
  }, []);

  return (
    <div>
      <h2>Notifications ({unreadCount} unread)</h2>
      {history.map(notification => (
        <div key={notification.id}>
          {notification.title}
        </div>
      ))}
    </div>
  );
}
```

### Configuration

#### Get Current Config

```typescript
const { config } = useNotificationStore();

console.log(config.position);        // 'top-right'
console.log(config.defaultDuration); // 5000
console.log(config.maxVisible);      // 5
```

#### Update Config

```typescript
const { updateConfig } = useNotificationStore();

await updateConfig({
  position: 'bottom-right',
  defaultDuration: 3000,
  maxVisible: 10,
});
```

### Available Configuration Options

```typescript
interface NotificationConfig {
  // Where notifications appear
  position: 'top-left' | 'top-right' | 'top-center' |
            'bottom-left' | 'bottom-right' | 'bottom-center';

  // Auto-dismiss duration in milliseconds
  defaultDuration: number;

  // Maximum simultaneously visible toasts
  maxVisible: number;

  // Sound effects (not yet implemented)
  soundEnabled: boolean;
}
```

---

## Backend Usage

### Using the Notification Service

The notification service is available through dependency injection:

```python
from fastapi import Depends
from recursive_neon.dependencies import ServiceContainer, get_container
from recursive_neon.models.notification import NotificationCreate, NotificationType

@app.post("/api/my-endpoint")
async def my_endpoint(
    container: ServiceContainer = Depends(get_container)
):
    # Create notification
    notification = container.notification_service.create_notification(
        NotificationCreate(
            title="Process Started",
            message="Your data processing has begun",
            type=NotificationType.INFO,
            source="data-processor"
        )
    )

    return {"notification_id": notification.id}
```

### Service Methods

```python
# Get notification service
notification_service = container.notification_service

# Create notification
notification = notification_service.create_notification(data)

# Get specific notification
notification = notification_service.get_notification(notification_id)

# List notifications with filters
filters = NotificationFilters(
    type=NotificationType.ERROR,
    read=False,
    limit=50
)
notifications = notification_service.list_notifications(filters)

# Update notification
updated = notification_service.update_notification(
    notification_id,
    NotificationUpdate(read=True)
)

# Delete notification
success = notification_service.delete_notification(notification_id)

# Clear all
count = notification_service.clear_all_notifications()

# Get unread count
count = notification_service.get_unread_count()

# Get/update configuration
config = notification_service.get_config()
config = notification_service.update_config(new_config)
```

### Filtering Notifications

```python
from recursive_neon.models.notification import NotificationFilters, NotificationType

# Filter by type
filters = NotificationFilters(type=NotificationType.ERROR)

# Filter by source
filters = NotificationFilters(source="my-app")

# Filter by read status
filters = NotificationFilters(read=False)  # Unread only

# Pagination
filters = NotificationFilters(limit=20, offset=40)

# Combined filters
filters = NotificationFilters(
    type=NotificationType.WARNING,
    source="security-scanner",
    read=False,
    limit=10,
    offset=0
)

notifications = notification_service.list_notifications(filters)
```

---

## API Reference

### HTTP Endpoints

#### Create Notification

```
POST /api/notifications
Content-Type: application/json

{
  "title": "Notification Title",
  "message": "Optional message",
  "type": "success",
  "source": "app-name"
}

Response: 201 Created
{
  "id": "uuid",
  "title": "Notification Title",
  "message": "Optional message",
  "type": "success",
  "source": "app-name",
  "created_at": "2025-11-15T12:30:00Z",
  "read": false,
  "dismissed": false
}
```

#### List Notifications

```
GET /api/notifications?type=info&source=app-name&read=false&limit=50&offset=0

Response: 200 OK
[
  {
    "id": "uuid",
    "title": "...",
    ...
  }
]
```

#### Get Single Notification

```
GET /api/notifications/{id}

Response: 200 OK
{
  "id": "uuid",
  ...
}
```

#### Update Notification

```
PATCH /api/notifications/{id}
Content-Type: application/json

{
  "read": true,
  "dismissed": true
}

Response: 200 OK
{
  "id": "uuid",
  "read": true,
  ...
}
```

#### Delete Notification

```
DELETE /api/notifications/{id}

Response: 204 No Content
```

#### Clear All Notifications

```
DELETE /api/notifications

Response: 200 OK
{
  "deleted_count": 42
}
```

#### Get Unread Count

```
GET /api/notifications/unread-count

Response: 200 OK
{
  "count": 5
}
```

#### Get Configuration

```
GET /api/notifications/config

Response: 200 OK
{
  "position": "top-right",
  "default_duration": 5000,
  "max_visible": 5,
  "sound_enabled": false
}
```

#### Update Configuration

```
PUT /api/notifications/config
Content-Type: application/json

{
  "position": "bottom-right",
  "default_duration": 3000
}

Response: 200 OK
{
  "position": "bottom-right",
  "default_duration": 3000,
  "max_visible": 5,
  "sound_enabled": false
}
```

### WebSocket Events

The system broadcasts these events via WebSocket:

#### notification_created

```json
{
  "type": "notification_created",
  "data": {
    "id": "uuid",
    "title": "...",
    ...
  }
}
```

#### notification_updated

```json
{
  "type": "notification_updated",
  "data": {
    "id": "uuid",
    "read": true,
    ...
  }
}
```

#### notification_deleted

```json
{
  "type": "notification_deleted",
  "data": {
    "id": "uuid"
  }
}
```

#### notifications_cleared

```json
{
  "type": "notifications_cleared",
  "data": {
    "count": 42
  }
}
```

#### notification_config_updated

```json
{
  "type": "notification_config_updated",
  "data": {
    "position": "bottom-right",
    ...
  }
}
```

---

## Examples

### Example 1: File Operation Success

```typescript
// In FileBrowserApp
const handleSaveFile = async () => {
  try {
    await saveFile(fileData);

    await createNotification({
      title: 'File Saved',
      message: `${fileName} has been saved successfully`,
      type: NotificationType.SUCCESS,
      source: 'file-browser',
    });
  } catch (error) {
    await createNotification({
      title: 'Save Failed',
      message: error.message,
      type: NotificationType.ERROR,
      source: 'file-browser',
    });
  }
};
```

### Example 2: Background Task Completion

```python
# Backend service
async def process_data(data: dict, container: ServiceContainer):
    try:
        # Long-running task
        result = await perform_processing(data)

        # Notify success
        container.notification_service.create_notification(
            NotificationCreate(
                title="Processing Complete",
                message=f"Processed {result.count} items successfully",
                type=NotificationType.SUCCESS,
                source="data-processor"
            )
        )
    except Exception as e:
        # Notify error
        container.notification_service.create_notification(
            NotificationCreate(
                title="Processing Failed",
                message=str(e),
                type=NotificationType.ERROR,
                source="data-processor"
            )
        )
```

### Example 3: Warning for Low Disk Space

```typescript
// Monitoring service
const checkDiskSpace = async () => {
  const spaceRemaining = await getAvailableSpace();

  if (spaceRemaining < 100) { // Less than 100MB
    await createNotification({
      title: 'Low Disk Space',
      message: `Only ${spaceRemaining}MB remaining`,
      type: NotificationType.WARNING,
      source: 'system-monitor',
    });
  }
};
```

### Example 4: Info Notification for New Features

```typescript
// On app startup
useEffect(() => {
  const hasSeenFeature = localStorage.getItem('seen-calendar-feature');

  if (!hasSeenFeature) {
    createNotification({
      title: 'New Feature Available',
      message: 'Check out the new Calendar app!',
      type: NotificationType.INFO,
      source: 'system',
    });

    localStorage.setItem('seen-calendar-feature', 'true');
  }
}, []);
```

---

## Best Practices

### 1. Choose the Right Type

- **INFO**: General information, tips, feature announcements
- **SUCCESS**: Successful operations (save, delete, create, etc.)
- **WARNING**: Non-critical issues that need attention
- **ERROR**: Failed operations, critical errors

### 2. Write Clear Titles

```typescript
// Good
title: 'File Saved'
title: 'Connection Lost'
title: 'Update Available'

// Avoid
title: 'Success'
title: 'Error'
title: 'Notification'
```

### 3. Provide Context in Messages

```typescript
// Good
title: 'Upload Failed'
message: 'Connection timeout after 30 seconds. Please check your network.'

// Less helpful
title: 'Upload Failed'
message: 'An error occurred'
```

### 4. Use Consistent Source Names

```typescript
// Good: Use consistent app identifiers
source: 'file-browser'
source: 'chat'
source: 'calendar'

// Avoid: Inconsistent naming
source: 'FileBrowser'
source: 'chat app'
source: 'calendar-v2'
```

### 5. Don't Spam Notifications

```typescript
// Bad: Creating notification in a loop
items.forEach(item => {
  createNotification({ title: `Processed ${item.name}` });
});

// Good: Single summary notification
createNotification({
  title: 'Batch Processing Complete',
  message: `Successfully processed ${items.length} items`,
});
```

### 6. Handle Errors Gracefully

```typescript
try {
  await createNotification({ ... });
} catch (error) {
  // Don't create another notification about notification failure
  console.error('Failed to create notification:', error);
}
```

### 7. Mark Notifications as Read

When user views notification details, mark it as read:

```typescript
const handleNotificationClick = async (notification: Notification) => {
  if (!notification.read) {
    await markAsRead(notification.id);
  }

  // Show details...
};
```

---

## Troubleshooting

### Notifications Not Appearing

**Problem**: Notifications aren't showing up

**Solutions**:
1. Check that NotificationContainer is rendered in Desktop component
2. Verify WebSocket connection is established
3. Check browser console for errors
4. Verify backend is running and notification service is initialized

### Notifications Not Persisting

**Problem**: Notifications disappear on page reload

**Solutions**:
1. Ensure backend is saving game state on shutdown
2. Check that `loadHistory()` is called on app initialization
3. Verify game_data directory has write permissions

### WebSocket Events Not Working

**Problem**: Real-time updates not appearing

**Solutions**:
1. Check WebSocket connection in browser DevTools (Network tab)
2. Verify event handlers are registered in App.tsx
3. Check backend is broadcasting events via `manager.broadcast()`

### Styling Issues

**Problem**: Notifications look broken or unstyled

**Solutions**:
1. Verify desktop.css is loaded
2. Check for CSS conflicts with other components
3. Ensure notification CSS is at the end of desktop.css

### TypeScript Errors

**Problem**: Type errors in notification code

**Solutions**:
1. Ensure notification models are imported correctly
2. Check that NotificationType enum is used
3. Verify notification store types match API types

---

## Testing

### Frontend Unit Tests

```typescript
import { useNotificationStore } from '../stores/notificationStore';
import { renderHook, act } from '@testing-library/react';

describe('Notification Store', () => {
  it('creates notification', async () => {
    const { result } = renderHook(() => useNotificationStore());

    await act(async () => {
      await result.current.createNotification({
        title: 'Test',
        source: 'test',
      });
    });

    expect(result.current.history.length).toBe(1);
  });
});
```

### Backend Unit Tests

```python
def test_create_notification(notification_service):
    data = NotificationCreate(
        title="Test",
        source="test"
    )

    notification = notification_service.create_notification(data)

    assert notification.title == "Test"
    assert notification.source == "test"
    assert notification.id is not None
```

---

## Summary

The RecursiveNeon notification system provides a robust, type-safe way to communicate with users. Key points to remember:

- Use appropriate notification types
- Provide clear, actionable messages
- Don't spam users with notifications
- Mark notifications as read when viewed
- Handle errors gracefully
- Test notification code thoroughly

For more information, see:
- [Requirements Document](./NOTIFICATION_SYSTEM_REQUIREMENTS.md)
- [Design Document](./NOTIFICATION_SYSTEM_DESIGN.md)
- [Backend Tests](../backend/tests/unit/test_notification_service.py)

---

*Last updated: 2025-11-15*
