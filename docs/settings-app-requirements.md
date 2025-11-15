# Settings App Requirements

> **Version**: 1.0
> **Date**: 2025-11-15
> **Project**: Recursive://Neon
> **Status**: Draft

---

## Table of Contents

1. [Overview](#overview)
2. [Goals and Objectives](#goals-and-objectives)
3. [Functional Requirements](#functional-requirements)
4. [Non-Functional Requirements](#non-functional-requirements)
5. [Data Models](#data-models)
6. [UI Requirements](#ui-requirements)
7. [Extensibility Requirements](#extensibility-requirements)
8. [Settings Categories](#settings-categories)
9. [Use Cases](#use-cases)
10. [Out of Scope](#out-of-scope)

---

## Overview

The Settings App provides a centralized, extensible system for managing game configuration. It includes:
- A desktop application with a categorized interface
- Backend service for persistent settings storage
- Extensible architecture for adding new settings pages
- Initial implementations for clock and theme settings

---

## Goals and Objectives

### Primary Goals

1. **Centralized Configuration**: Single location for all game settings
2. **Extensibility**: Easy for new features to add settings pages
3. **Persistence**: Settings persist across sessions
4. **User-Friendly**: Clear, intuitive interface
5. **Backend Authority**: Backend maintains authoritative settings state
6. **Real-Time Updates**: Changes take effect immediately

### Secondary Goals

1. **Categorization**: Settings organized by category/feature
2. **Search**: Ability to search for settings (future)
3. **Reset**: Ability to reset to defaults
4. **Import/Export**: Export and import settings (future)

---

## Functional Requirements

### FR-1: Settings Application UI

**FR-1.1**: The settings app SHALL be a desktop window application.

**FR-1.2**: The app SHALL have a sidebar showing categories/pages.

**FR-1.3**: The app SHALL have a main content area showing the selected page.

**FR-1.4**: The app SHALL be accessible from the desktop (system icon).

**FR-1.5**: The app SHALL support standard window operations (minimize, maximize, close).

### FR-2: Settings Pages System

**FR-2.1**: The system SHALL support multiple settings pages.

**FR-2.2**: Each page SHALL have:
- Unique identifier
- Display name
- Icon
- Category (optional, for grouping)
- React component for rendering

**FR-2.3**: Pages SHALL be registered in a central registry.

**FR-2.4**: New pages SHALL be addable by:
- Creating a component
- Registering in the page registry
- No modification of core settings code required

**FR-2.5**: Pages SHALL be displayed in alphabetical order within categories.

### FR-3: Settings Storage

**FR-3.1**: Settings SHALL be stored in the backend.

**FR-3.2**: Each setting SHALL have:
- Unique key (namespaced by feature)
- Value (any JSON-serializable type)
- Default value
- Schema/validation (optional)

**FR-3.3**: Settings SHALL be persisted to disk.

**FR-3.4**: Settings SHALL be loaded on startup.

**FR-3.5**: Settings file SHALL be JSON format.

### FR-4: Settings API

**FR-4.1**: The system SHALL provide API to:
- Get a single setting by key
- Get all settings
- Set a single setting
- Set multiple settings
- Reset a setting to default
- Reset all settings to defaults

**FR-4.2**: Setting changes SHALL be immediately persisted.

**FR-4.3**: Setting changes SHALL be broadcast to all connected clients.

**FR-4.4**: Invalid setting values SHALL be rejected with clear error messages.

### FR-5: Clock Settings

**FR-5.1**: Clock settings page SHALL control:
- Clock visibility (show/hide)
- Clock mode (analog/digital/off)
- Clock position (top-right, top-left, bottom-right, bottom-left)
- 12/24 hour format (digital mode)
- Show seconds (digital mode)
- Show date (digital mode)

**FR-5.2**: Changes to clock settings SHALL take effect immediately.

**FR-5.3**: Clock settings SHALL persist across sessions.

**FR-5.4**: Default clock settings:
- Visible: true
- Mode: digital
- Position: top-right
- Format: 24-hour
- Show seconds: true
- Show date: true

### FR-6: Theme Settings

**FR-6.1**: Theme settings page SHALL allow selection from predefined themes.

**FR-6.2**: Available themes SHALL include:
- Classic (current blue theme)
- Dark Mode (dark backgrounds, light text)
- Light Mode (light backgrounds, dark text)
- Neon (bright neon colors)
- Terminal (green on black, retro terminal)
- Cyberpunk (purple/pink neon aesthetic)

**FR-6.3**: Theme changes SHALL apply immediately to all UI elements.

**FR-6.4**: Theme SHALL persist across sessions.

**FR-6.5**: Each theme SHALL define:
- Primary colors
- Background colors
- Text colors
- Accent colors
- Border colors
- Window styling

**FR-6.6**: Default theme: Classic

### FR-7: Settings Validation

**FR-7.1**: Each setting SHALL have optional validation rules.

**FR-7.2**: Validation failures SHALL prevent setting changes.

**FR-7.3**: Validation errors SHALL be shown to the user.

**FR-7.4**: Common validation types:
- Type checking (string, number, boolean, enum)
- Range validation (min/max for numbers)
- Enum validation (value must be in list)
- Custom validation functions

### FR-8: Default Values

**FR-8.1**: Every setting SHALL have a default value.

**FR-8.2**: If no saved value exists, default SHALL be used.

**FR-8.3**: User SHALL be able to reset individual settings to defaults.

**FR-8.4**: User SHALL be able to reset all settings to defaults.

**FR-8.5**: Reset actions SHALL require confirmation.

### FR-9: Real-Time Synchronization

**FR-9.1**: When a client changes a setting, the change SHALL be broadcast to all clients.

**FR-9.2**: All clients SHALL update their local state when receiving setting changes.

**FR-9.3**: UI elements SHALL update when settings change.

**FR-9.4**: If multiple clients change the same setting simultaneously, last write wins.

---

## Non-Functional Requirements

### NFR-1: Performance

**NFR-1.1**: Settings reads SHALL complete in <1ms.

**NFR-1.2**: Settings writes SHALL complete in <50ms (including disk write).

**NFR-1.3**: Settings file SHALL load in <100ms.

**NFR-1.4**: Theme changes SHALL apply in <500ms.

### NFR-2: Reliability

**NFR-2.1**: Settings SHALL never be corrupted or lost.

**NFR-2.2**: Invalid settings SHALL fall back to defaults.

**NFR-2.3**: Corrupted settings file SHALL be backed up and recreated.

**NFR-2.4**: Settings writes SHALL be atomic (write to temp file, then rename).

### NFR-3: Usability

**NFR-3.1**: Settings UI SHALL be intuitive and self-explanatory.

**NFR-3.2**: Changes SHALL take effect immediately (no "Apply" button needed).

**NFR-3.3**: Settings SHALL have clear labels and descriptions.

**NFR-3.4**: Related settings SHALL be grouped together.

### NFR-4: Extensibility

**NFR-4.1**: Adding a new settings page SHALL require <50 lines of code.

**NFR-4.2**: New settings SHALL not require changes to core settings service.

**NFR-4.3**: Settings schema SHALL be easily extended.

**NFR-4.4**: Third-party features SHALL be able to add settings pages.

### NFR-5: Maintainability

**NFR-5.1**: Settings service SHALL follow DI patterns.

**NFR-5.2**: Settings service SHALL have >85% test coverage.

**NFR-5.3**: Settings service SHALL use type hints.

**NFR-5.4**: Settings service SHALL be documented.

---

## Data Models

### Setting

Individual setting with metadata.

```python
class Setting(BaseModel):
    key: str                        # Unique key (e.g., "clock.visible")
    value: Any                      # Current value
    default_value: Any              # Default value
    value_type: str                 # "string" | "number" | "boolean" | "enum"
    description: Optional[str]      # Human-readable description
    enum_values: Optional[List[Any]] # Valid values for enum type
    min_value: Optional[float]      # Min for number type
    max_value: Optional[float]      # Max for number type
```

### SettingsState

Complete settings state.

```python
class SettingsState(BaseModel):
    settings: Dict[str, Any]        # Key-value pairs of all settings
    last_modified: datetime         # Last modification time
```

### SettingUpdate

Message sent when settings change.

```python
class SettingUpdate(BaseModel):
    key: str                        # Setting key that changed
    value: Any                      # New value
    timestamp: datetime             # When the change occurred
```

### SettingsPage

Frontend page registration.

```typescript
interface SettingsPage {
  id: string;                       // Unique page ID
  name: string;                     // Display name
  icon: string;                     // Icon (emoji or icon class)
  category?: string;                // Category for grouping
  component: React.ComponentType;   // Component to render
  order?: number;                   // Display order (optional)
}
```

### Theme

Theme definition.

```typescript
interface Theme {
  id: string;                       // Unique theme ID
  name: string;                     // Display name
  colors: {
    primary: string;
    secondary: string;
    background: string;
    surface: string;
    text: string;
    textSecondary: string;
    border: string;
    accent: string;
    success: string;
    warning: string;
    error: string;
    taskbarBackground: string;
    windowTitleBar: string;
  };
  fonts: {
    primary: string;
    monospace: string;
  };
}
```

---

## UI Requirements

### Layout

```
┌─────────────────────────────────────────────┐
│ ⚙️ Settings                          [─][□][✕]│
├──────────┬──────────────────────────────────┤
│          │                                  │
│ General  │  Clock Settings                  │
│          │                                  │
│ 🕐 Clock │  Display:                        │
│ 🎨 Theme │    ○ Hidden                      │
│          │    ○ Analog                      │
│ System   │    ● Digital                     │
│          │                                  │
│ 🔊 Audio │  Position: [Top Right ▼]         │
│          │                                  │
│ Advanced │  □ Show seconds                  │
│          │  ☑ Show date                     │
│ 🐛 Debug │  ○ 12-hour  ● 24-hour           │
│          │                                  │
│          │                                  │
│          │              [Reset to Defaults] │
└──────────┴──────────────────────────────────┘
```

### UI Components

**Sidebar**:
- Category headers (bold)
- Page items (icon + name)
- Highlight selected page
- Hover effects

**Content Area**:
- Page title
- Settings controls
- Help text/descriptions
- Reset button

**Control Types**:
- Checkboxes (boolean settings)
- Radio buttons (enum with few options)
- Dropdowns (enum with many options)
- Sliders (numeric with range)
- Text inputs (strings)
- Color pickers (colors)

---

## Extensibility Requirements

### Adding a New Settings Page

To add a new settings page, developers should only need to:

1. **Create the component**:
```typescript
// components/apps/settings/AudioSettingsPage.tsx
export function AudioSettingsPage() {
  const { settings, updateSetting } = useSettings();

  return (
    <div className="settings-page">
      <h2>Audio Settings</h2>
      {/* Settings controls */}
    </div>
  );
}
```

2. **Register the page**:
```typescript
// components/apps/settings/settingsPages.ts
import { AudioSettingsPage } from './AudioSettingsPage';

export const settingsPages: SettingsPage[] = [
  // ... existing pages
  {
    id: 'audio',
    name: 'Audio',
    icon: '🔊',
    category: 'System',
    component: AudioSettingsPage,
  },
];
```

That's it! No changes to core settings infrastructure needed.

### Settings Namespace Convention

Settings keys should be namespaced by feature:

- `clock.*` - Clock-related settings
- `theme.*` - Theme-related settings
- `audio.*` - Audio settings
- `terminal.*` - Terminal settings
- `notifications.*` - Notification settings

Example keys:
- `clock.visible`
- `clock.mode`
- `theme.current`
- `audio.volume`
- `audio.muted`

---

## Settings Categories

### Initial Categories

1. **General** (no category header)
   - Clock
   - Theme

2. **System**
   - Audio (future)
   - Notifications (future)

3. **Advanced**
   - Debug
   - Developer Tools (future)

### Category Organization

- Categories group related pages
- Categories appear as headers in sidebar
- Pages within categories are alphabetically sorted
- General category items appear at the top without a header

---

## Use Cases

### UC-1: User Opens Settings App

1. User clicks Settings icon on desktop
2. Settings window opens
3. Backend sends current settings state
4. UI displays Clock settings page (first page)
5. All settings show current values

### UC-2: User Changes Clock Mode

1. User opens Settings app
2. User clicks "Clock" in sidebar
3. User selects "Analog" radio button
4. Frontend sends update to backend
5. Backend persists setting
6. Backend broadcasts change to all clients
7. Clock widget updates to analog mode

### UC-3: User Changes Theme

1. User opens Settings app
2. User clicks "Theme" in sidebar
3. User selects "Dark Mode" from dropdown
4. Frontend sends update to backend
5. Backend persists setting
6. Backend broadcasts change to all clients
7. All windows re-render with dark theme
8. CSS variables update
9. Theme applies smoothly

### UC-4: User Resets Settings

1. User opens Settings app
2. User clicks "Reset to Defaults" button
3. Confirmation dialog appears
4. User confirms
5. Backend resets all settings to defaults
6. Backend broadcasts updates
7. All UI elements update to defaults
8. Success message shown

### UC-5: Developer Adds New Settings Page

1. Developer creates `NotificationSettingsPage.tsx`
2. Developer adds component to settings page registry
3. Developer defines settings keys in backend
4. Page automatically appears in settings sidebar
5. Settings persist and synchronize automatically

### UC-6: Multiple Clients

1. User A and User B both have game open
2. User A changes theme to Dark Mode
3. Backend receives change from User A
4. Backend broadcasts to all clients
5. User B's UI updates to Dark Mode
6. Both clients now show Dark Mode

### UC-7: Settings File Corruption

1. Backend loads settings on startup
2. Settings file is corrupted (invalid JSON)
3. Backend logs error
4. Backend backs up corrupted file
5. Backend creates new settings with defaults
6. Game starts successfully with default settings
7. User can reconfigure settings

---

## Out of Scope

The following are explicitly out of scope for v1.0:

1. **Settings Search**: No search functionality
2. **Settings Import/Export**: No backup/restore
3. **Settings Profiles**: No multiple profiles
4. **Settings History**: No undo/redo
5. **Settings Sync**: No cloud sync
6. **Settings Validation UI**: No complex form validation
7. **Settings Dependencies**: No conditional settings (if A then show B)
8. **Settings Permissions**: All settings accessible to all users
9. **Settings Encryption**: Settings stored in plain JSON
10. **Settings Migration**: No automatic migration from old versions

---

## Initial Settings

### Clock Settings (clock.*)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `clock.visible` | boolean | true | Show/hide clock |
| `clock.mode` | enum | "digital" | "off", "analog", "digital" |
| `clock.position` | enum | "top-right" | "top-left", "top-right", "bottom-left", "bottom-right" |
| `clock.format` | enum | "24h" | "12h", "24h" |
| `clock.showSeconds` | boolean | true | Show seconds in digital mode |
| `clock.showDate` | boolean | true | Show date with time |

### Theme Settings (theme.*)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `theme.current` | enum | "classic" | "classic", "dark", "light", "neon", "terminal", "cyberpunk" |

---

## Acceptance Criteria

The settings app shall be considered complete when:

1. ✅ Settings backend service is implemented
2. ✅ Settings persist to disk and load on startup
3. ✅ Settings desktop app is functional
4. ✅ Clock settings page is implemented
5. ✅ Theme settings page is implemented
6. ✅ At least 3 themes are implemented
7. ✅ Settings changes take effect immediately
8. ✅ Settings synchronize across multiple clients
9. ✅ New settings pages can be added without modifying core code
10. ✅ Reset to defaults functionality works
11. ✅ Unit tests achieve >85% coverage
12. ✅ UI is intuitive and polished
13. ✅ Documentation is complete

---

## Future Enhancements

Potential future additions (not in v1.0):

1. **Settings Search**: Search bar to find settings
2. **Settings Categories Collapse**: Collapsible category headers
3. **Settings Descriptions**: Tooltip or help text for each setting
4. **Settings Import/Export**: Backup and restore settings
5. **Settings Profiles**: Multiple named profiles
6. **Settings Keyboard Shortcuts**: Keyboard navigation
7. **Settings Change Log**: History of setting changes
8. **Settings Validation Feedback**: Real-time validation with helpful errors
9. **Settings Dependencies**: Show/hide settings based on other settings
10. **Advanced Settings**: Expert mode with advanced options
11. **Settings Cloud Sync**: Sync settings across devices
12. **Custom Themes**: User-created themes with theme editor

---

**Document Status**: Ready for review
**Next Steps**: Create design document and begin implementation
