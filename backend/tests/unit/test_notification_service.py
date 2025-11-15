"""Unit tests for NotificationService.

This module contains comprehensive tests for the NotificationService class,
covering all CRUD operations, filtering, configuration, and edge cases.
"""

import pytest
from datetime import datetime
from recursive_neon.models.game_state import GameState
from recursive_neon.models.notification import (
    Notification,
    NotificationCreate,
    NotificationUpdate,
    NotificationFilters,
    NotificationConfig,
    NotificationType
)
from recursive_neon.services.notification_service import NotificationService


class TestNotificationService:
    """Test suite for NotificationService"""

    @pytest.fixture
    def game_state(self):
        """Create a fresh GameState for each test"""
        return GameState()

    @pytest.fixture
    def notification_service(self, game_state):
        """Create a NotificationService with game state"""
        return NotificationService(game_state)

    @pytest.fixture
    def sample_notification_create(self):
        """Sample notification creation data"""
        return NotificationCreate(
            title="Test Notification",
            message="This is a test message",
            type=NotificationType.INFO,
            source="test-app"
        )

    # ========================================================================
    # Initialization Tests
    # ========================================================================

    def test_initialization(self, notification_service, game_state):
        """Test service initialization"""
        assert notification_service.game_state is game_state
        assert hasattr(game_state, 'notifications')
        assert hasattr(game_state, 'notification_config')
        assert isinstance(game_state.notifications, list)
        assert isinstance(game_state.notification_config, NotificationConfig)

    def test_initialization_creates_notifications_list(self):
        """Test that initialization creates notifications list if missing"""
        game_state = GameState()
        delattr(game_state, 'notifications')

        service = NotificationService(game_state)

        assert hasattr(game_state, 'notifications')
        assert game_state.notifications == []

    def test_initialization_creates_config(self):
        """Test that initialization creates config if missing"""
        game_state = GameState()
        delattr(game_state, 'notification_config')

        service = NotificationService(game_state)

        assert hasattr(game_state, 'notification_config')
        assert isinstance(game_state.notification_config, NotificationConfig)

    # ========================================================================
    # Create Notification Tests
    # ========================================================================

    def test_create_notification_basic(
        self,
        notification_service,
        sample_notification_create
    ):
        """Test creating a basic notification"""
        notification = notification_service.create_notification(
            sample_notification_create
        )

        assert isinstance(notification, Notification)
        assert notification.title == sample_notification_create.title
        assert notification.message == sample_notification_create.message
        assert notification.type == sample_notification_create.type
        assert notification.source == sample_notification_create.source
        assert notification.id  # Should have auto-generated ID
        assert isinstance(notification.created_at, datetime)
        assert notification.read is False
        assert notification.dismissed is False

    def test_create_notification_adds_to_game_state(
        self,
        notification_service,
        game_state,
        sample_notification_create
    ):
        """Test that creating notification adds it to game state"""
        initial_count = len(game_state.notifications)

        notification = notification_service.create_notification(
            sample_notification_create
        )

        assert len(game_state.notifications) == initial_count + 1
        assert notification in game_state.notifications

    def test_create_notification_all_types(self, notification_service):
        """Test creating notifications of all types"""
        types = [
            NotificationType.INFO,
            NotificationType.SUCCESS,
            NotificationType.WARNING,
            NotificationType.ERROR
        ]

        for notification_type in types:
            data = NotificationCreate(
                title=f"{notification_type.value} test",
                type=notification_type,
                source="test"
            )
            notification = notification_service.create_notification(data)

            assert notification.type == notification_type

    def test_create_notification_without_message(self, notification_service):
        """Test creating notification without optional message"""
        data = NotificationCreate(
            title="Title only",
            source="test"
        )

        notification = notification_service.create_notification(data)

        assert notification.title == "Title only"
        assert notification.message is None

    def test_create_multiple_notifications(self, notification_service):
        """Test creating multiple notifications"""
        notifications = []

        for i in range(5):
            data = NotificationCreate(
                title=f"Notification {i}",
                source="test"
            )
            notification = notification_service.create_notification(data)
            notifications.append(notification)

        # All should have unique IDs
        ids = [n.id for n in notifications]
        assert len(ids) == len(set(ids))  # No duplicates

    # ========================================================================
    # Get Notification Tests
    # ========================================================================

    def test_get_notification_existing(
        self,
        notification_service,
        sample_notification_create
    ):
        """Test getting an existing notification"""
        created = notification_service.create_notification(
            sample_notification_create
        )

        retrieved = notification_service.get_notification(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.title == created.title

    def test_get_notification_nonexistent(self, notification_service):
        """Test getting a non-existent notification"""
        result = notification_service.get_notification("nonexistent-id")

        assert result is None

    # ========================================================================
    # List Notifications Tests
    # ========================================================================

    def test_list_notifications_empty(self, notification_service):
        """Test listing notifications when none exist"""
        filters = NotificationFilters()

        results = notification_service.list_notifications(filters)

        assert results == []

    def test_list_notifications_all(self, notification_service):
        """Test listing all notifications"""
        # Create 3 notifications
        for i in range(3):
            data = NotificationCreate(
                title=f"Notification {i}",
                source="test"
            )
            notification_service.create_notification(data)

        filters = NotificationFilters()
        results = notification_service.list_notifications(filters)

        assert len(results) == 3

    def test_list_notifications_sorted_newest_first(self, notification_service):
        """Test that notifications are sorted newest first"""
        import time

        # Create notifications with slight delay
        for i in range(3):
            data = NotificationCreate(
                title=f"Notification {i}",
                source="test"
            )
            notification_service.create_notification(data)
            time.sleep(0.01)  # Small delay to ensure different timestamps

        filters = NotificationFilters()
        results = notification_service.list_notifications(filters)

        # Should be in reverse order (newest first)
        assert results[0].title == "Notification 2"
        assert results[1].title == "Notification 1"
        assert results[2].title == "Notification 0"

    def test_list_notifications_filter_by_type(self, notification_service):
        """Test filtering notifications by type"""
        # Create notifications of different types
        types_data = [
            (NotificationType.INFO, "info"),
            (NotificationType.SUCCESS, "success"),
            (NotificationType.WARNING, "warning"),
            (NotificationType.ERROR, "error"),
        ]

        for notification_type, title in types_data:
            data = NotificationCreate(
                title=title,
                type=notification_type,
                source="test"
            )
            notification_service.create_notification(data)

        # Filter for INFO only
        filters = NotificationFilters(type=NotificationType.INFO)
        results = notification_service.list_notifications(filters)

        assert len(results) == 1
        assert results[0].type == NotificationType.INFO

    def test_list_notifications_filter_by_source(self, notification_service):
        """Test filtering notifications by source"""
        # Create notifications from different sources
        sources = ["app1", "app2", "app1", "app3"]

        for source in sources:
            data = NotificationCreate(
                title=f"From {source}",
                source=source
            )
            notification_service.create_notification(data)

        # Filter for app1
        filters = NotificationFilters(source="app1")
        results = notification_service.list_notifications(filters)

        assert len(results) == 2
        assert all(n.source == "app1" for n in results)

    def test_list_notifications_filter_by_read_status(self, notification_service):
        """Test filtering notifications by read status"""
        # Create notifications
        for i in range(3):
            data = NotificationCreate(
                title=f"Notification {i}",
                source="test"
            )
            notification_service.create_notification(data)

        # Mark one as read
        all_notifications = notification_service.list_notifications(
            NotificationFilters()
        )
        notification_service.update_notification(
            all_notifications[0].id,
            NotificationUpdate(read=True)
        )

        # Filter for unread
        filters = NotificationFilters(read=False)
        results = notification_service.list_notifications(filters)

        assert len(results) == 2
        assert all(not n.read for n in results)

        # Filter for read
        filters = NotificationFilters(read=True)
        results = notification_service.list_notifications(filters)

        assert len(results) == 1
        assert results[0].read is True

    def test_list_notifications_pagination(self, notification_service):
        """Test pagination of notification list"""
        # Create 10 notifications
        for i in range(10):
            data = NotificationCreate(
                title=f"Notification {i}",
                source="test"
            )
            notification_service.create_notification(data)

        # Get first page (limit 3)
        filters = NotificationFilters(limit=3, offset=0)
        page1 = notification_service.list_notifications(filters)

        assert len(page1) == 3

        # Get second page
        filters = NotificationFilters(limit=3, offset=3)
        page2 = notification_service.list_notifications(filters)

        assert len(page2) == 3

        # Pages should not overlap
        page1_ids = [n.id for n in page1]
        page2_ids = [n.id for n in page2]
        assert not any(id in page2_ids for id in page1_ids)

    def test_list_notifications_combined_filters(self, notification_service):
        """Test combining multiple filters"""
        # Create various notifications
        notification_service.create_notification(NotificationCreate(
            title="Info from app1",
            type=NotificationType.INFO,
            source="app1"
        ))
        notification_service.create_notification(NotificationCreate(
            title="Success from app1",
            type=NotificationType.SUCCESS,
            source="app1"
        ))
        notification_service.create_notification(NotificationCreate(
            title="Info from app2",
            type=NotificationType.INFO,
            source="app2"
        ))

        # Filter for INFO type from app1
        filters = NotificationFilters(
            type=NotificationType.INFO,
            source="app1"
        )
        results = notification_service.list_notifications(filters)

        assert len(results) == 1
        assert results[0].type == NotificationType.INFO
        assert results[0].source == "app1"

    # ========================================================================
    # Update Notification Tests
    # ========================================================================

    def test_update_notification_mark_as_read(
        self,
        notification_service,
        sample_notification_create
    ):
        """Test marking notification as read"""
        notification = notification_service.create_notification(
            sample_notification_create
        )

        assert notification.read is False

        updated = notification_service.update_notification(
            notification.id,
            NotificationUpdate(read=True)
        )

        assert updated is not None
        assert updated.read is True
        assert updated.id == notification.id

    def test_update_notification_mark_as_unread(self, notification_service):
        """Test marking notification as unread"""
        data = NotificationCreate(title="Test", source="test")
        notification = notification_service.create_notification(data)

        # Mark as read first
        notification_service.update_notification(
            notification.id,
            NotificationUpdate(read=True)
        )

        # Then mark as unread
        updated = notification_service.update_notification(
            notification.id,
            NotificationUpdate(read=False)
        )

        assert updated.read is False

    def test_update_notification_mark_as_dismissed(
        self,
        notification_service,
        sample_notification_create
    ):
        """Test marking notification as dismissed"""
        notification = notification_service.create_notification(
            sample_notification_create
        )

        updated = notification_service.update_notification(
            notification.id,
            NotificationUpdate(dismissed=True)
        )

        assert updated.dismissed is True

    def test_update_notification_both_fields(
        self,
        notification_service,
        sample_notification_create
    ):
        """Test updating both read and dismissed status"""
        notification = notification_service.create_notification(
            sample_notification_create
        )

        updated = notification_service.update_notification(
            notification.id,
            NotificationUpdate(read=True, dismissed=True)
        )

        assert updated.read is True
        assert updated.dismissed is True

    def test_update_notification_nonexistent(self, notification_service):
        """Test updating non-existent notification"""
        result = notification_service.update_notification(
            "nonexistent-id",
            NotificationUpdate(read=True)
        )

        assert result is None

    def test_update_notification_partial(
        self,
        notification_service,
        sample_notification_create
    ):
        """Test partial update (only one field)"""
        notification = notification_service.create_notification(
            sample_notification_create
        )

        # Update only read status
        updated = notification_service.update_notification(
            notification.id,
            NotificationUpdate(read=True)
        )

        assert updated.read is True
        assert updated.dismissed is False  # Should remain unchanged

    # ========================================================================
    # Delete Notification Tests
    # ========================================================================

    def test_delete_notification_existing(
        self,
        notification_service,
        game_state,
        sample_notification_create
    ):
        """Test deleting an existing notification"""
        notification = notification_service.create_notification(
            sample_notification_create
        )

        initial_count = len(game_state.notifications)

        result = notification_service.delete_notification(notification.id)

        assert result is True
        assert len(game_state.notifications) == initial_count - 1
        assert notification_service.get_notification(notification.id) is None

    def test_delete_notification_nonexistent(self, notification_service):
        """Test deleting non-existent notification"""
        result = notification_service.delete_notification("nonexistent-id")

        assert result is False

    def test_delete_notification_leaves_others(self, notification_service):
        """Test that deleting one notification doesn't affect others"""
        # Create 3 notifications
        n1 = notification_service.create_notification(
            NotificationCreate(title="N1", source="test")
        )
        n2 = notification_service.create_notification(
            NotificationCreate(title="N2", source="test")
        )
        n3 = notification_service.create_notification(
            NotificationCreate(title="N3", source="test")
        )

        # Delete middle one
        notification_service.delete_notification(n2.id)

        # Others should still exist
        assert notification_service.get_notification(n1.id) is not None
        assert notification_service.get_notification(n2.id) is None
        assert notification_service.get_notification(n3.id) is not None

    # ========================================================================
    # Clear All Notifications Tests
    # ========================================================================

    def test_clear_all_notifications(self, notification_service, game_state):
        """Test clearing all notifications"""
        # Create several notifications
        for i in range(5):
            data = NotificationCreate(
                title=f"Notification {i}",
                source="test"
            )
            notification_service.create_notification(data)

        count = notification_service.clear_all_notifications()

        assert count == 5
        assert len(game_state.notifications) == 0

    def test_clear_all_notifications_when_empty(self, notification_service):
        """Test clearing notifications when none exist"""
        count = notification_service.clear_all_notifications()

        assert count == 0

    # ========================================================================
    # Unread Count Tests
    # ========================================================================

    def test_get_unread_count_zero(self, notification_service):
        """Test unread count when no notifications"""
        count = notification_service.get_unread_count()

        assert count == 0

    def test_get_unread_count_all_unread(self, notification_service):
        """Test unread count when all are unread"""
        for i in range(3):
            data = NotificationCreate(
                title=f"Notification {i}",
                source="test"
            )
            notification_service.create_notification(data)

        count = notification_service.get_unread_count()

        assert count == 3

    def test_get_unread_count_mixed(self, notification_service):
        """Test unread count with mixed read/unread"""
        # Create 5 notifications
        ids = []
        for i in range(5):
            data = NotificationCreate(
                title=f"Notification {i}",
                source="test"
            )
            notification = notification_service.create_notification(data)
            ids.append(notification.id)

        # Mark 2 as read
        notification_service.update_notification(
            ids[0],
            NotificationUpdate(read=True)
        )
        notification_service.update_notification(
            ids[2],
            NotificationUpdate(read=True)
        )

        count = notification_service.get_unread_count()

        assert count == 3  # 5 total - 2 read = 3 unread

    def test_get_unread_count_all_read(self, notification_service):
        """Test unread count when all are read"""
        # Create and mark all as read
        for i in range(3):
            data = NotificationCreate(
                title=f"Notification {i}",
                source="test"
            )
            notification = notification_service.create_notification(data)
            notification_service.update_notification(
                notification.id,
                NotificationUpdate(read=True)
            )

        count = notification_service.get_unread_count()

        assert count == 0

    # ========================================================================
    # Configuration Tests
    # ========================================================================

    def test_get_config_default(self, notification_service):
        """Test getting default configuration"""
        config = notification_service.get_config()

        assert isinstance(config, NotificationConfig)
        assert config.position == "top-right"
        assert config.default_duration == 5000
        assert config.max_visible == 5
        assert config.sound_enabled is False

    def test_update_config(self, notification_service):
        """Test updating configuration"""
        new_config = NotificationConfig(
            position="bottom-left",
            default_duration=3000,
            max_visible=10,
            sound_enabled=True
        )

        updated = notification_service.update_config(new_config)

        assert updated.position == "bottom-left"
        assert updated.default_duration == 3000
        assert updated.max_visible == 10
        assert updated.sound_enabled is True

    def test_update_config_persists(self, notification_service, game_state):
        """Test that config update persists in game state"""
        new_config = NotificationConfig(position="bottom-right")

        notification_service.update_config(new_config)

        assert game_state.notification_config.position == "bottom-right"

    def test_get_config_after_update(self, notification_service):
        """Test getting config after update"""
        new_config = NotificationConfig(default_duration=7000)
        notification_service.update_config(new_config)

        retrieved = notification_service.get_config()

        assert retrieved.default_duration == 7000
