/**
 * Settings Service for frontend settings management
 *
 * This service manages application settings by:
 * - Syncing with backend authoritative settings
 * - Providing get/set API for settings
 * - Notifying subscribers of changes
 * - Supporting settings validation
 */

export type SettingValue = string | number | boolean;
export type SettingsMap = Record<string, SettingValue>;

type SettingChangeCallback = (key: string, value: SettingValue) => void;

export class SettingsService {
  private settings: SettingsMap;
  private subscribers: SettingChangeCallback[];
  private wsClient: any | null;  // WebSocket client reference

  constructor() {
    this.settings = {};
    this.subscribers = [];
    this.wsClient = null;
  }

  /**
   * Initialize with WebSocket client.
   */
  initialize(wsClient: any): void {
    this.wsClient = wsClient;

    // Request initial settings
    this.fetchAll();
  }

  /**
   * Fetch all settings from backend.
   */
  async fetchAll(): Promise<void> {
    if (!this.wsClient) return;

    this.wsClient.sendMessage({
      type: 'settings',
      data: {
        action: 'get_all',
      },
    });
  }

  /**
   * Get a setting value.
   */
  get(key: string): SettingValue | undefined {
    return this.settings[key];
  }

  /**
   * Get all settings.
   */
  getAll(): SettingsMap {
    return { ...this.settings };
  }

  /**
   * Set a setting value.
   */
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

  /**
   * Set multiple settings.
   */
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

  /**
   * Reset a setting to default.
   */
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

  /**
   * Reset all settings to defaults.
   */
  async resetAll(): Promise<void> {
    if (!this.wsClient) return;

    this.wsClient.sendMessage({
      type: 'settings',
      data: {
        action: 'reset_all',
      },
    });
  }

  /**
   * Subscribe to setting changes.
   */
  subscribe(callback: SettingChangeCallback): () => void {
    this.subscribers.push(callback);
    return () => {
      const index = this.subscribers.indexOf(callback);
      if (index > -1) {
        this.subscribers.splice(index, 1);
      }
    };
  }

  /**
   * Handle settings response from backend.
   */
  handleSettingsResponse(message: any): void {
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

  /**
   * Handle setting update from backend.
   */
  handleSettingUpdate(message: any): void {
    const { key, value } = message.data;
    this.settings[key] = value;
    this.notifySubscribers(key, value);
  }

  /**
   * Handle settings update (multiple settings) from backend.
   */
  handleSettingsUpdate(message: any): void {
    const updates = message.data.settings;
    Object.keys(updates).forEach(key => {
      this.settings[key] = updates[key];
      this.notifySubscribers(key, updates[key]);
    });
  }

  /**
   * Notify subscribers of setting change.
   */
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

export const settingsService = new SettingsService();
