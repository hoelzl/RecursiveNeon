# Settings App Design

> **Version**: 1.0
> **Date**: 2025-11-15
> **Project**: Recursive://Neon
> **Status**: Draft

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Backend Design](#backend-design)
3. [Frontend Design](#frontend-design)
4. [Extensibility System](#extensibility-system)
5. [Theme System](#theme-system)
6. [Clock Settings Integration](#clock-settings-integration)
7. [Data Flow](#data-flow)
8. [Implementation Details](#implementation-details)
9. [Testing Strategy](#testing-strategy)

---

## Architecture Overview

### High-Level Architecture

```
┌───────────────────────────────────────────────────────────┐
│                     Frontend                              │
│                                                           │
│  ┌────────────────────────────────────────────┐          │
│  │  Settings App (Desktop Window)             │          │
│  │                                            │          │
│  │  ┌─────────┐  ┌──────────────────────┐    │          │
│  │  │Sidebar  │  │  Content Area        │    │          │
│  │  │         │  │                      │    │          │
│  │  │🕐 Clock │  │ <SettingsPage />    │    │          │
│  │  │🎨 Theme │  │                      │    │          │
│  │  │         │  │  (dynamically        │    │          │
│  │  │         │  │   rendered)          │    │          │
│  │  └─────────┘  └──────────────────────┘    │          │
│  └────────────────────────────────────────────┘          │
│                        ▲                                  │
│                        │                                  │
│  ┌────────────────────┴───────────────┐                  │
│  │  SettingsService                   │                  │
│  │  - Get/set settings                │                  │
│  │  - Subscribe to changes            │                  │
│  │  - Sync with backend               │                  │
│  └────────────┬───────────────────────┘                  │
│               │                                           │
│  ┌────────────┴───────────────┐                          │
│  │  ThemeService              │                          │
│  │  - Apply themes            │                          │
│  │  - CSS variable management │                          │
│  └────────────────────────────┘                          │
│                                                           │
└───────────────────────┬───────────────────────────────────┘
                        │ WebSocket
┌───────────────────────┼───────────────────────────────────┐
│                  Backend                                  │
│                       ▼                                   │
│  ┌──────────────────────────────────────────┐            │
│  │  MessageHandler                          │            │
│  │  (routes settings messages)              │            │
│  └──────────────┬───────────────────────────┘            │
│                 │                                         │
│                 ▼                                         │
│  ┌──────────────────────────────────────────┐            │
│  │  SettingsService                         │            │
│  │                                           │            │
│  │  - In-memory settings store              │            │
│  │  - Validation                             │            │
│  │  - Persistence                            │            │
│  │  - Change broadcasting                    │            │
│  │                                           │            │
│  │  ┌──────────────┐   ┌──────────────┐    │            │
│  │  │SettingsStore │◄──┤SettingsPersist│   │            │
│  │  │(in-memory)   │   │(JSON file)    │    │            │
│  │  └──────────────┘   └──────────────┘    │            │
│  └──────────────────────────────────────────┘            │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Extensibility**: New settings pages added with minimal code
2. **Type Safety**: Settings schema with validation
3. **Real-Time Sync**: Changes broadcast to all clients
4. **Persistence**: Settings survive restarts
5. **Separation of Concerns**: Backend stores, frontend renders
6. **Theme Integration**: Theme system affects all UI components

---

## Backend Design

### SettingsService Interface

```python
# backend/src/recursive_neon/services/interfaces.py

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable

class ISettingsService(ABC):
    """Interface for settings management."""

    @abstractmethod
    def get(self, key: str) -> Any:
        """Get a setting value."""
        pass

    @abstractmethod
    def get_all(self) -> Dict[str, Any]:
        """Get all settings."""
        pass

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Set a setting value."""
        pass

    @abstractmethod
    def set_many(self, settings: Dict[str, Any]) -> None:
        """Set multiple settings at once."""
        pass

    @abstractmethod
    def reset(self, key: str) -> None:
        """Reset a setting to its default value."""
        pass

    @abstractmethod
    def reset_all(self) -> None:
        """Reset all settings to defaults."""
        pass

    @abstractmethod
    def get_default(self, key: str) -> Any:
        """Get the default value for a setting."""
        pass

    @abstractmethod
    def register_default(self, key: str, default_value: Any, validator: Optional[Callable] = None) -> None:
        """Register a default value and optional validator."""
        pass

    @abstractmethod
    def save(self) -> None:
        """Save settings to disk."""
        pass

    @abstractmethod
    def load(self) -> None:
        """Load settings from disk."""
        pass

    @abstractmethod
    def subscribe(self, callback: Callable[[str, Any], None]) -> None:
        """Subscribe to setting changes."""
        pass
```

### SettingsService Implementation

```python
# backend/src/recursive_neon/services/settings_service.py

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
from pydantic import BaseModel, ValidationError

from recursive_neon.services.interfaces import ISettingsService

logger = logging.getLogger(__name__)

class SettingDefinition:
    """Definition of a setting with validation."""

    def __init__(
        self,
        key: str,
        default_value: Any,
        validator: Optional[Callable[[Any], bool]] = None,
        description: Optional[str] = None,
    ):
        self.key = key
        self.default_value = default_value
        self.validator = validator
        self.description = description

    def validate(self, value: Any) -> bool:
        """Validate a value."""
        if self.validator:
            return self.validator(value)
        return True

class SettingsService(ISettingsService):
    """Settings management service."""

    def __init__(self, persistence_path: Optional[Path] = None):
        """Initialize settings service."""
        self.persistence_path = persistence_path
        self._settings: Dict[str, Any] = {}
        self._defaults: Dict[str, SettingDefinition] = {}
        self._callbacks: List[Callable[[str, Any], None]] = []

        # Register default settings
        self._register_default_settings()

        # Load saved settings
        if persistence_path and persistence_path.exists():
            try:
                self.load()
            except Exception as e:
                logger.warning(f"Failed to load settings: {e}, using defaults")

    def _register_default_settings(self) -> None:
        """Register all default settings."""

        # Clock settings
        self.register_default("clock.visible", True)
        self.register_default(
            "clock.mode",
            "digital",
            validator=lambda v: v in ["off", "analog", "digital"],
        )
        self.register_default(
            "clock.position",
            "top-right",
            validator=lambda v: v in ["top-left", "top-right", "bottom-left", "bottom-right"],
        )
        self.register_default(
            "clock.format",
            "24h",
            validator=lambda v: v in ["12h", "24h"],
        )
        self.register_default("clock.showSeconds", True)
        self.register_default("clock.showDate", True)

        # Theme settings
        self.register_default(
            "theme.current",
            "classic",
            validator=lambda v: v in ["classic", "dark", "light", "neon", "terminal", "cyberpunk"],
        )

    def register_default(
        self,
        key: str,
        default_value: Any,
        validator: Optional[Callable[[Any], bool]] = None,
        description: Optional[str] = None,
    ) -> None:
        """Register a default setting."""
        definition = SettingDefinition(key, default_value, validator, description)
        self._defaults[key] = definition

        # If no value exists, use default
        if key not in self._settings:
            self._settings[key] = default_value

    def get(self, key: str) -> Any:
        """Get a setting value."""
        if key in self._settings:
            return self._settings[key]

        # Return default if exists
        if key in self._defaults:
            return self._defaults[key].default_value

        raise KeyError(f"Setting '{key}' not found")

    def get_all(self) -> Dict[str, Any]:
        """Get all settings."""
        return dict(self._settings)

    def set(self, key: str, value: Any) -> None:
        """Set a setting value."""
        # Validate if validator exists
        if key in self._defaults:
            if not self._defaults[key].validate(value):
                raise ValueError(f"Invalid value for setting '{key}': {value}")

        old_value = self._settings.get(key)
        self._settings[key] = value

        # Notify subscribers if value changed
        if old_value != value:
            self._notify_change(key, value)
            self.save()

    def set_many(self, settings: Dict[str, Any]) -> None:
        """Set multiple settings."""
        # Validate all first
        for key, value in settings.items():
            if key in self._defaults:
                if not self._defaults[key].validate(value):
                    raise ValueError(f"Invalid value for setting '{key}': {value}")

        # Apply all
        changed_keys = []
        for key, value in settings.items():
            old_value = self._settings.get(key)
            self._settings[key] = value
            if old_value != value:
                changed_keys.append(key)

        # Notify for each changed key
        for key in changed_keys:
            self._notify_change(key, self._settings[key])

        if changed_keys:
            self.save()

    def reset(self, key: str) -> None:
        """Reset setting to default."""
        if key not in self._defaults:
            raise KeyError(f"Setting '{key}' has no default")

        default_value = self._defaults[key].default_value
        self.set(key, default_value)

    def reset_all(self) -> None:
        """Reset all settings to defaults."""
        for key, definition in self._defaults.items():
            self._settings[key] = definition.default_value

        # Notify all changes
        for key in self._defaults.keys():
            self._notify_change(key, self._settings[key])

        self.save()

    def get_default(self, key: str) -> Any:
        """Get default value."""
        if key not in self._defaults:
            raise KeyError(f"Setting '{key}' has no default")
        return self._defaults[key].default_value

    def save(self) -> None:
        """Save settings to disk."""
        if not self.persistence_path:
            return

        try:
            # Atomic write
            temp_path = self.persistence_path.with_suffix('.tmp')
            with open(temp_path, 'w') as f:
                json.dump(self._settings, f, indent=2)
            temp_path.replace(self.persistence_path)

            logger.debug(f"Saved settings to {self.persistence_path}")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def load(self) -> None:
        """Load settings from disk."""
        if not self.persistence_path or not self.persistence_path.exists():
            return

        try:
            with open(self.persistence_path, 'r') as f:
                loaded_settings = json.load(f)

            # Validate and apply
            for key, value in loaded_settings.items():
                if key in self._defaults:
                    if self._defaults[key].validate(value):
                        self._settings[key] = value
                    else:
                        logger.warning(f"Invalid value for '{key}': {value}, using default")
                else:
                    # Unknown setting, but keep it
                    self._settings[key] = value

            logger.info(f"Loaded settings from {self.persistence_path}")
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            raise

    def subscribe(self, callback: Callable[[str, Any], None]) -> None:
        """Subscribe to changes."""
        self._callbacks.append(callback)

    def _notify_change(self, key: str, value: Any) -> None:
        """Notify subscribers of change."""
        for callback in self._callbacks:
            try:
                callback(key, value)
            except Exception as e:
                logger.error(f"Error in settings callback: {e}")
```

### Integration with MessageHandler

```python
# backend/src/recursive_neon/services/message_handler.py

async def _handle_settings_message(self, data: dict) -> Dict[str, Any]:
    """Handle settings messages."""
    action = data.get("action")

    if action == "get_all":
        return {
            "type": "settings_response",
            "data": {
                "settings": self.settings_service.get_all()
            }
        }

    elif action == "get":
        key = data.get("key")
        if not key:
            return {"type": "error", "message": "Missing key"}

        try:
            value = self.settings_service.get(key)
            return {
                "type": "settings_response",
                "data": {
                    "key": key,
                    "value": value
                }
            }
        except KeyError as e:
            return {"type": "error", "message": str(e)}

    elif action == "set":
        key = data.get("key")
        value = data.get("value")

        if not key:
            return {"type": "error", "message": "Missing key"}

        try:
            self.settings_service.set(key, value)
            return {
                "type": "setting_update",
                "data": {
                    "key": key,
                    "value": value
                }
            }
        except (KeyError, ValueError) as e:
            return {"type": "error", "message": str(e)}

    elif action == "set_many":
        settings = data.get("settings")
        if not settings:
            return {"type": "error", "message": "Missing settings"}

        try:
            self.settings_service.set_many(settings)
            return {
                "type": "settings_update",
                "data": {
                    "settings": settings
                }
            }
        except (KeyError, ValueError) as e:
            return {"type": "error", "message": str(e)}

    elif action == "reset":
        key = data.get("key")
        if not key:
            return {"type": "error", "message": "Missing key"}

        try:
            self.settings_service.reset(key)
            value = self.settings_service.get(key)
            return {
                "type": "setting_update",
                "data": {
                    "key": key,
                    "value": value
                }
            }
        except KeyError as e:
            return {"type": "error", "message": str(e)}

    elif action == "reset_all":
        self.settings_service.reset_all()
        return {
            "type": "settings_update",
            "data": {
                "settings": self.settings_service.get_all()
            }
        }

    else:
        return {"type": "error", "message": f"Unknown settings action: {action}"}
```

---

## Frontend Design

### SettingsService (Frontend)

```typescript
// frontend/src/services/settingsService.ts

export type SettingValue = string | number | boolean;
export type SettingsMap = Record<string, SettingValue>;

type SettingChangeCallback = (key: string, value: SettingValue) => void;

export class SettingsService {
  private settings: SettingsMap;
  private subscribers: SettingChangeCallback[];
  private wsClient: WebSocketClient | null;

  constructor() {
    this.settings = {};
    this.subscribers = [];
    this.wsClient = null;
  }

  initialize(wsClient: WebSocketClient): void {
    this.wsClient = wsClient;

    // Subscribe to settings updates
    wsClient.addMessageHandler('settings_response', this.handleSettingsResponse.bind(this));
    wsClient.addMessageHandler('setting_update', this.handleSettingUpdate.bind(this));
    wsClient.addMessageHandler('settings_update', this.handleSettingsUpdate.bind(this));

    // Request initial settings
    this.fetchAll();
  }

  async fetchAll(): Promise<void> {
    if (!this.wsClient) return;

    this.wsClient.sendMessage({
      type: 'settings',
      data: {
        action: 'get_all',
      },
    });
  }

  get(key: string): SettingValue | undefined {
    return this.settings[key];
  }

  getAll(): SettingsMap {
    return { ...this.settings };
  }

  async set(key: string, value: SettingValue): Promise<void> {
    if (!this.wsClient) return;

    this.wsClient.sendMessage({
      type: 'settings',
      data: {
        action: 'set',
        key,
        value,
      },
    });
  }

  async setMany(settings: SettingsMap): Promise<void> {
    if (!this.wsClient) return;

    this.wsClient.sendMessage({
      type: 'settings',
      data: {
        action: 'set_many',
        settings,
      },
    });
  }

  async reset(key: string): Promise<void> {
    if (!this.wsClient) return;

    this.wsClient.sendMessage({
      type: 'settings',
      data: {
        action: 'reset',
        key,
      },
    });
  }

  async resetAll(): Promise<void> {
    if (!this.wsClient) return;

    this.wsClient.sendMessage({
      type: 'settings',
      data: {
        action: 'reset_all',
      },
    });
  }

  subscribe(callback: SettingChangeCallback): () => void {
    this.subscribers.push(callback);
    return () => {
      const index = this.subscribers.indexOf(callback);
      if (index > -1) {
        this.subscribers.splice(index, 1);
      }
    };
  }

  private handleSettingsResponse(message: any): void {
    const data = message.data;

    if (data.settings) {
      // Full settings update
      this.settings = data.settings;
      // Notify about all changes
      Object.keys(this.settings).forEach(key => {
        this.notifySubscribers(key, this.settings[key]);
      });
    } else if (data.key && data.value !== undefined) {
      // Single setting
      this.settings[data.key] = data.value;
      this.notifySubscribers(data.key, data.value);
    }
  }

  private handleSettingUpdate(message: any): void {
    const { key, value } = message.data;
    this.settings[key] = value;
    this.notifySubscribers(key, value);
  }

  private handleSettingsUpdate(message: any): void {
    const updates = message.data.settings;
    Object.keys(updates).forEach(key => {
      this.settings[key] = updates[key];
      this.notifySubscribers(key, updates[key]);
    });
  }

  private notifySubscribers(key: string, value: SettingValue): void {
    this.subscribers.forEach(callback => {
      try {
        callback(key, value);
      } catch (error) {
        console.error('Error in settings callback:', error);
      }
    });
  }
}
```

### SettingsService Context

```typescript
// frontend/src/contexts/SettingsServiceContext.tsx

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { SettingsService, SettingsMap, SettingValue } from '../services/settingsService';
import { useWebSocket } from './WebSocketContext';

interface SettingsServiceContextType {
  settingsService: SettingsService;
  settings: SettingsMap;
  getSetting: (key: string) => SettingValue | undefined;
  setSetting: (key: string, value: SettingValue) => Promise<void>;
}

const SettingsServiceContext = createContext<SettingsServiceContextType | null>(null);

export function SettingsServiceProvider({ children }: { children: ReactNode }) {
  const wsClient = useWebSocket();
  const [settingsService] = useState(() => new SettingsService());
  const [settings, setSettings] = useState<SettingsMap>({});

  useEffect(() => {
    if (wsClient) {
      settingsService.initialize(wsClient);
    }
  }, [wsClient, settingsService]);

  useEffect(() => {
    const unsubscribe = settingsService.subscribe((key, value) => {
      setSettings(prev => ({ ...prev, [key]: value }));
    });
    return unsubscribe;
  }, [settingsService]);

  const getSetting = (key: string) => settingsService.get(key);
  const setSetting = (key: string, value: SettingValue) => settingsService.set(key, value);

  return (
    <SettingsServiceContext.Provider value={{ settingsService, settings, getSetting, setSetting }}>
      {children}
    </SettingsServiceContext.Provider>
  );
}

export function useSettings(): SettingsServiceContextType {
  const context = useContext(SettingsServiceContext);
  if (!context) {
    throw new Error('useSettings must be used within SettingsServiceProvider');
  }
  return context;
}
```

### Settings App Component

```typescript
// frontend/src/components/apps/SettingsApp.tsx

import React, { useState } from 'react';
import { settingsPages } from './settings/settingsPages';
import './SettingsApp.css';

export function SettingsApp() {
  const [selectedPageId, setSelectedPageId] = useState(settingsPages[0]?.id || '');

  const selectedPage = settingsPages.find(p => p.id === selectedPageId);
  const PageComponent = selectedPage?.component;

  // Group pages by category
  const categorized: Record<string, typeof settingsPages> = {};
  const uncategorized: typeof settingsPages = [];

  settingsPages.forEach(page => {
    if (page.category) {
      if (!categorized[page.category]) {
        categorized[page.category] = [];
      }
      categorized[page.category].push(page);
    } else {
      uncategorized.push(page);
    }
  });

  return (
    <div className="settings-app">
      <div className="settings-sidebar">
        {/* Uncategorized pages (General) */}
        {uncategorized.map(page => (
          <div
            key={page.id}
            className={`settings-page-item ${selectedPageId === page.id ? 'selected' : ''}`}
            onClick={() => setSelectedPageId(page.id)}
          >
            <span className="settings-page-icon">{page.icon}</span>
            <span className="settings-page-name">{page.name}</span>
          </div>
        ))}

        {/* Categorized pages */}
        {Object.entries(categorized).map(([category, pages]) => (
          <div key={category} className="settings-category">
            <div className="settings-category-header">{category}</div>
            {pages.map(page => (
              <div
                key={page.id}
                className={`settings-page-item ${selectedPageId === page.id ? 'selected' : ''}`}
                onClick={() => setSelectedPageId(page.id)}
              >
                <span className="settings-page-icon">{page.icon}</span>
                <span className="settings-page-name">{page.name}</span>
              </div>
            ))}
          </div>
        ))}
      </div>

      <div className="settings-content">
        {PageComponent && <PageComponent />}
      </div>
    </div>
  );
}
```

---

## Extensibility System

### Settings Page Registry

```typescript
// frontend/src/components/apps/settings/settingsPages.ts

import { ComponentType } from 'react';
import { ClockSettingsPage } from './ClockSettingsPage';
import { ThemeSettingsPage } from './ThemeSettingsPage';

export interface SettingsPage {
  id: string;
  name: string;
  icon: string;
  category?: string;
  component: ComponentType;
  order?: number;
}

export const settingsPages: SettingsPage[] = [
  {
    id: 'clock',
    name: 'Clock',
    icon: '🕐',
    component: ClockSettingsPage,
  },
  {
    id: 'theme',
    name: 'Theme',
    icon: '🎨',
    component: ThemeSettingsPage,
  },
  // More pages added here...
];

// Sort by category then order
settingsPages.sort((a, b) => {
  if (a.category !== b.category) {
    return (a.category || '').localeCompare(b.category || '');
  }
  return (a.order || 0) - (b.order || 0);
});
```

### Adding a New Page - Example

```typescript
// frontend/src/components/apps/settings/AudioSettingsPage.tsx

import React from 'react';
import { useSettings } from '../../../contexts/SettingsServiceContext';

export function AudioSettingsPage() {
  const { settings, setSetting } = useSettings();

  return (
    <div className="settings-page">
      <h2>Audio Settings</h2>

      <div className="setting-group">
        <label>
          Master Volume
          <input
            type="range"
            min="0"
            max="100"
            value={settings['audio.volume'] as number || 100}
            onChange={e => setSetting('audio.volume', parseInt(e.target.value))}
          />
          <span>{settings['audio.volume'] || 100}%</span>
        </label>
      </div>

      <div className="setting-group">
        <label>
          <input
            type="checkbox"
            checked={settings['audio.muted'] as boolean || false}
            onChange={e => setSetting('audio.muted', e.target.checked)}
          />
          Mute all sounds
        </label>
      </div>
    </div>
  );
}

// Then register in settingsPages.ts:
// import { AudioSettingsPage } from './AudioSettingsPage';
//
// settingsPages.push({
//   id: 'audio',
//   name: 'Audio',
//   icon: '🔊',
//   category: 'System',
//   component: AudioSettingsPage,
// });
```

---

## Theme System

### Theme Definitions

```typescript
// frontend/src/themes/themes.ts

export interface Theme {
  id: string;
  name: string;
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
}

export const themes: Theme[] = [
  {
    id: 'classic',
    name: 'Classic',
    colors: {
      primary: '#0066CC',
      secondary: '#004999',
      background: '#008080',
      surface: '#C0C0C0',
      text: '#000000',
      textSecondary: '#666666',
      border: '#808080',
      accent: '#0066CC',
      success: '#00AA00',
      warning: '#FF8800',
      error: '#CC0000',
      taskbarBackground: '#C0C0C0',
      windowTitleBar: '#000080',
    },
  },
  {
    id: 'dark',
    name: 'Dark Mode',
    colors: {
      primary: '#3391FF',
      secondary: '#1F5FA8',
      background: '#1E1E1E',
      surface: '#2D2D2D',
      text: '#E0E0E0',
      textSecondary: '#A0A0A0',
      border: '#404040',
      accent: '#3391FF',
      success: '#4CAF50',
      warning: '#FF9800',
      error: '#F44336',
      taskbarBackground: '#252525',
      windowTitleBar: '#1E1E1E',
    },
  },
  {
    id: 'light',
    name: 'Light Mode',
    colors: {
      primary: '#2196F3',
      secondary: '#1976D2',
      background: '#FAFAFA',
      surface: '#FFFFFF',
      text: '#212121',
      textSecondary: '#757575',
      border: '#E0E0E0',
      accent: '#2196F3',
      success: '#4CAF50',
      warning: '#FF9800',
      error: '#F44336',
      taskbarBackground: '#F5F5F5',
      windowTitleBar: '#2196F3',
    },
  },
  {
    id: 'neon',
    name: 'Neon',
    colors: {
      primary: '#FF00FF',
      secondary: '#CC00CC',
      background: '#000033',
      surface: '#1A1A3E',
      text: '#00FFFF',
      textSecondary: '#FF00FF',
      border: '#FF00FF',
      accent: '#00FFFF',
      success: '#00FF00',
      warning: '#FFFF00',
      error: '#FF0066',
      taskbarBackground: '#0F0F2E',
      windowTitleBar: '#FF00FF',
    },
  },
  {
    id: 'terminal',
    name: 'Terminal',
    colors: {
      primary: '#00FF00',
      secondary: '#00AA00',
      background: '#000000',
      surface: '#0A0A0A',
      text: '#00FF00',
      textSecondary: '#008800',
      border: '#00FF00',
      accent: '#00FF00',
      success: '#00FF00',
      warning: '#FFFF00',
      error: '#FF0000',
      taskbarBackground: '#000000',
      windowTitleBar: '#000000',
    },
  },
  {
    id: 'cyberpunk',
    name: 'Cyberpunk',
    colors: {
      primary: '#FF10F0',
      secondary: '#AA00AA',
      background: '#0D001A',
      surface: '#1A0033',
      text: '#F0F0FF',
      textSecondary: '#B0B0FF',
      border: '#FF10F0',
      accent: '#00FFFF',
      success: '#00FF88',
      warning: '#FFAA00',
      error: '#FF0066',
      taskbarBackground: '#1A0033',
      windowTitleBar: '#2D0052',
    },
  },
];

export function getTheme(id: string): Theme | undefined {
  return themes.find(t => t.id === id);
}
```

### Theme Application

```typescript
// frontend/src/services/themeService.ts

import { themes, getTheme } from '../themes/themes';

export class ThemeService {
  applyTheme(themeId: string): void {
    const theme = getTheme(themeId);
    if (!theme) {
      console.error(`Theme '${themeId}' not found`);
      return;
    }

    // Apply CSS variables
    const root = document.documentElement;
    Object.entries(theme.colors).forEach(([key, value]) => {
      const cssVarName = `--color-${this.kebabCase(key)}`;
      root.style.setProperty(cssVarName, value);
    });

    console.log(`Applied theme: ${theme.name}`);
  }

  private kebabCase(str: string): string {
    return str.replace(/([a-z])([A-Z])/g, '$1-$2').toLowerCase();
  }
}

// Usage in CSS:
// .window-title-bar {
//   background: var(--color-window-title-bar);
//   color: var(--color-text);
// }
```

### Theme Integration with Settings

```typescript
// Update SettingsServiceProvider to apply themes

useEffect(() => {
  const themeService = new ThemeService();
  const currentTheme = settings['theme.current'] as string;

  if (currentTheme) {
    themeService.applyTheme(currentTheme);
  }
}, [settings]);
```

---

## Clock Settings Integration

### Clock Settings Page

```typescript
// frontend/src/components/apps/settings/ClockSettingsPage.tsx

import React from 'react';
import { useSettings } from '../../../contexts/SettingsServiceContext';

export function ClockSettingsPage() {
  const { settings, setSetting } = useSettings();

  return (
    <div className="settings-page">
      <h2>Clock Settings</h2>

      <div className="setting-group">
        <h3>Display Mode</h3>
        <label>
          <input
            type="radio"
            name="clock-mode"
            value="off"
            checked={settings['clock.mode'] === 'off'}
            onChange={e => setSetting('clock.mode', e.target.value)}
          />
          Hidden
        </label>
        <label>
          <input
            type="radio"
            name="clock-mode"
            value="analog"
            checked={settings['clock.mode'] === 'analog'}
            onChange={e => setSetting('clock.mode', e.target.value)}
          />
          Analog
        </label>
        <label>
          <input
            type="radio"
            name="clock-mode"
            value="digital"
            checked={settings['clock.mode'] === 'digital'}
            onChange={e => setSetting('clock.mode', e.target.value)}
          />
          Digital
        </label>
      </div>

      <div className="setting-group">
        <h3>Position</h3>
        <select
          value={settings['clock.position'] as string || 'top-right'}
          onChange={e => setSetting('clock.position', e.target.value)}
        >
          <option value="top-left">Top Left</option>
          <option value="top-right">Top Right</option>
          <option value="bottom-left">Bottom Left</option>
          <option value="bottom-right">Bottom Right</option>
        </select>
      </div>

      {settings['clock.mode'] === 'digital' && (
        <>
          <div className="setting-group">
            <h3>Digital Clock Options</h3>
            <label>
              <input
                type="checkbox"
                checked={settings['clock.showSeconds'] as boolean || true}
                onChange={e => setSetting('clock.showSeconds', e.target.checked)}
              />
              Show seconds
            </label>
            <label>
              <input
                type="checkbox"
                checked={settings['clock.showDate'] as boolean || true}
                onChange={e => setSetting('clock.showDate', e.target.checked)}
              />
              Show date
            </label>
          </div>

          <div className="setting-group">
            <h3>Time Format</h3>
            <label>
              <input
                type="radio"
                name="clock-format"
                value="12h"
                checked={settings['clock.format'] === '12h'}
                onChange={e => setSetting('clock.format', e.target.value)}
              />
              12-hour (AM/PM)
            </label>
            <label>
              <input
                type="radio"
                name="clock-format"
                value="24h"
                checked={settings['clock.format'] === '24h'}
                onChange={e => setSetting('clock.format', e.target.value)}
              />
              24-hour
            </label>
          </div>
        </>
      )}

      <div className="setting-actions">
        <button onClick={() => {
          setSetting('clock.mode', 'digital');
          setSetting('clock.position', 'top-right');
          setSetting('clock.format', '24h');
          setSetting('clock.showSeconds', true);
          setSetting('clock.showDate', true);
        }}>
          Reset to Defaults
        </button>
      </div>
    </div>
  );
}
```

---

## Data Flow

### Settings Change Flow

```
1. User changes setting in Settings App
2. Frontend calls settingsService.set(key, value)
3. SettingsService sends WebSocket message to backend
4. Backend SettingsService validates and updates
5. Backend persists to disk
6. Backend broadcasts update to ALL clients
7. All frontends receive update
8. All frontends update local state
9. UI elements re-render with new value
```

### Initial Load Flow

```
1. Frontend connects WebSocket
2. SettingsService.initialize() called
3. Sends "get_all" message to backend
4. Backend responds with all settings
5. Frontend updates local state
6. UI renders with correct settings
```

---

## Implementation Details

### File Structure

**Backend**:
- `backend/src/recursive_neon/services/interfaces.py` - Add ISettingsService
- `backend/src/recursive_neon/services/settings_service.py` - Implementation
- `backend/src/recursive_neon/dependencies.py` - Add to container
- `backend/src/recursive_neon/services/message_handler.py` - Add handlers
- `backend/tests/unit/test_settings_service.py` - Tests

**Frontend**:
- `frontend/src/services/settingsService.ts` - Service
- `frontend/src/contexts/SettingsServiceContext.tsx` - Context
- `frontend/src/components/apps/SettingsApp.tsx` - Main app
- `frontend/src/components/apps/settings/settingsPages.ts` - Registry
- `frontend/src/components/apps/settings/ClockSettingsPage.tsx` - Clock page
- `frontend/src/components/apps/settings/ThemeSettingsPage.tsx` - Theme page
- `frontend/src/themes/themes.ts` - Theme definitions
- `frontend/src/services/themeService.ts` - Theme application
- `frontend/src/components/apps/SettingsApp.css` - Styles
- `frontend/src/test/settingsService.test.ts` - Tests

---

## Testing Strategy

### Backend Tests

```python
class TestSettingsService:
    def test_get_default_setting(self):
        service = SettingsService()
        assert service.get("clock.visible") == True

    def test_set_and_get(self):
        service = SettingsService()
        service.set("clock.mode", "analog")
        assert service.get("clock.mode") == "analog"

    def test_validation_rejects_invalid(self):
        service = SettingsService()
        with pytest.raises(ValueError):
            service.set("clock.mode", "invalid_mode")

    def test_persistence(self, tmp_path):
        path = tmp_path / "settings.json"

        service1 = SettingsService(persistence_path=path)
        service1.set("clock.mode", "analog")
        service1.save()

        service2 = SettingsService(persistence_path=path)
        service2.load()
        assert service2.get("clock.mode") == "analog"

    def test_reset_to_default(self):
        service = SettingsService()
        service.set("clock.mode", "analog")
        service.reset("clock.mode")
        assert service.get("clock.mode") == "digital"

    def test_notifications(self):
        service = SettingsService()
        notifications = []

        service.subscribe(lambda k, v: notifications.append((k, v)))
        service.set("clock.mode", "analog")

        assert len(notifications) == 1
        assert notifications[0] == ("clock.mode", "analog")
```

### Frontend Tests

```typescript
describe('SettingsService', () => {
  test('fetches all settings on initialize', () => {
    const service = new SettingsService();
    const mockWs = createMockWebSocket();

    service.initialize(mockWs);

    expect(mockWs.sendMessage).toHaveBeenCalledWith({
      type: 'settings',
      data: { action: 'get_all' },
    });
  });

  test('updates local state on settings response', () => {
    const service = new SettingsService();
    const callback = jest.fn();

    service.subscribe(callback);

    service['handleSettingsResponse']({
      data: {
        settings: {
          'clock.mode': 'analog',
          'theme.current': 'dark',
        },
      },
    });

    expect(callback).toHaveBeenCalledTimes(2);
    expect(service.get('clock.mode')).toBe('analog');
  });

  test('sends set message', () => {
    const service = new SettingsService();
    const mockWs = createMockWebSocket();
    service.initialize(mockWs);

    service.set('clock.mode', 'analog');

    expect(mockWs.sendMessage).toHaveBeenCalledWith({
      type: 'settings',
      data: {
        action: 'set',
        key: 'clock.mode',
        value: 'analog',
      },
    });
  });
});
```

---

**Document Status**: Ready for implementation
**Next Steps**: Begin backend implementation with SettingsService
