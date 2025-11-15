/**
 * Tests for SettingsService
 *
 * Tests frontend settings management and synchronization.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { SettingsService } from './settingsService';

describe('SettingsService', () => {
  let settingsService: SettingsService;
  let mockWsClient: any;

  beforeEach(() => {
    settingsService = new SettingsService();

    // Mock WebSocket client
    mockWsClient = {
      sendMessage: vi.fn(),
    };
  });

  describe('Initialization', () => {
    it('should initialize with empty settings', () => {
      const all = settingsService.getAll();

      expect(all).toEqual({});
    });

    it('should fetch all settings on initialize', () => {
      settingsService.initialize(mockWsClient);

      expect(mockWsClient.sendMessage).toHaveBeenCalledWith({
        type: 'settings',
        data: {
          action: 'get_all',
        },
      });
    });
  });

  describe('Getting Settings', () => {
    it('should get a setting value', () => {
      settingsService['settings'] = {
        'clock.mode': 'digital',
      };

      expect(settingsService.get('clock.mode')).toBe('digital');
    });

    it('should return undefined for nonexistent setting', () => {
      expect(settingsService.get('nonexistent')).toBeUndefined();
    });

    it('should get all settings', () => {
      settingsService['settings'] = {
        'clock.mode': 'digital',
        'theme.current': 'dark',
      };

      const all = settingsService.getAll();

      expect(all).toEqual({
        'clock.mode': 'digital',
        'theme.current': 'dark',
      });
    });

    it('should return a copy of settings (not the original)', () => {
      settingsService['settings'] = {
        'clock.mode': 'digital',
      };

      const all = settingsService.getAll();
      all['clock.mode'] = 'analog';

      // Original should not be modified
      expect(settingsService.get('clock.mode')).toBe('digital');
    });
  });

  describe('Setting Values', () => {
    beforeEach(() => {
      settingsService.initialize(mockWsClient);
      mockWsClient.sendMessage.mockClear();
    });

    it('should send set message', async () => {
      await settingsService.set('clock.mode', 'analog');

      expect(mockWsClient.sendMessage).toHaveBeenCalledWith({
        type: 'settings',
        data: {
          action: 'set',
          key: 'clock.mode',
          value: 'analog',
        },
      });
    });

    it('should send set_many message', async () => {
      const settings = {
        'clock.mode': 'analog',
        'theme.current': 'dark',
      };

      await settingsService.setMany(settings);

      expect(mockWsClient.sendMessage).toHaveBeenCalledWith({
        type: 'settings',
        data: {
          action: 'set_many',
          settings,
        },
      });
    });
  });

  describe('Reset Methods', () => {
    beforeEach(() => {
      settingsService.initialize(mockWsClient);
      mockWsClient.sendMessage.mockClear();
    });

    it('should send reset message', async () => {
      await settingsService.reset('clock.mode');

      expect(mockWsClient.sendMessage).toHaveBeenCalledWith({
        type: 'settings',
        data: {
          action: 'reset',
          key: 'clock.mode',
        },
      });
    });

    it('should send reset_all message', async () => {
      await settingsService.resetAll();

      expect(mockWsClient.sendMessage).toHaveBeenCalledWith({
        type: 'settings',
        data: {
          action: 'reset_all',
        },
      });
    });
  });

  describe('Message Handlers', () => {
    it('should handle full settings response', () => {
      const callback = vi.fn();
      settingsService.subscribe(callback);

      settingsService.handleSettingsResponse({
        data: {
          settings: {
            'clock.mode': 'analog',
            'theme.current': 'dark',
          },
        },
      });

      expect(settingsService.get('clock.mode')).toBe('analog');
      expect(settingsService.get('theme.current')).toBe('dark');

      // Should notify for each setting
      expect(callback).toHaveBeenCalledWith('clock.mode', 'analog');
      expect(callback).toHaveBeenCalledWith('theme.current', 'dark');
    });

    it('should handle single setting response', () => {
      const callback = vi.fn();
      settingsService.subscribe(callback);

      settingsService.handleSettingsResponse({
        data: {
          key: 'clock.mode',
          value: 'analog',
        },
      });

      expect(settingsService.get('clock.mode')).toBe('analog');
      expect(callback).toHaveBeenCalledWith('clock.mode', 'analog');
    });

    it('should handle setting update', () => {
      const callback = vi.fn();
      settingsService.subscribe(callback);

      settingsService.handleSettingUpdate({
        data: {
          key: 'clock.mode',
          value: 'digital',
        },
      });

      expect(settingsService.get('clock.mode')).toBe('digital');
      expect(callback).toHaveBeenCalledWith('clock.mode', 'digital');
    });

    it('should handle settings update (multiple)', () => {
      const callback = vi.fn();
      settingsService.subscribe(callback);

      settingsService.handleSettingsUpdate({
        data: {
          settings: {
            'clock.mode': 'analog',
            'theme.current': 'neon',
          },
        },
      });

      expect(settingsService.get('clock.mode')).toBe('analog');
      expect(settingsService.get('theme.current')).toBe('neon');

      expect(callback).toHaveBeenCalledWith('clock.mode', 'analog');
      expect(callback).toHaveBeenCalledWith('theme.current', 'neon');
    });
  });

  describe('Subscriptions', () => {
    it('should notify subscribers on setting change', () => {
      const callback = vi.fn();

      settingsService.subscribe(callback);

      settingsService.handleSettingUpdate({
        data: {
          key: 'clock.mode',
          value: 'analog',
        },
      });

      expect(callback).toHaveBeenCalledWith('clock.mode', 'analog');
    });

    it('should allow unsubscribing', () => {
      const callback = vi.fn();

      const unsubscribe = settingsService.subscribe(callback);
      unsubscribe();

      settingsService.handleSettingUpdate({
        data: {
          key: 'clock.mode',
          value: 'analog',
        },
      });

      expect(callback).not.toHaveBeenCalled();
    });

    it('should notify multiple subscribers', () => {
      const callback1 = vi.fn();
      const callback2 = vi.fn();

      settingsService.subscribe(callback1);
      settingsService.subscribe(callback2);

      settingsService.handleSettingUpdate({
        data: {
          key: 'clock.mode',
          value: 'analog',
        },
      });

      expect(callback1).toHaveBeenCalledWith('clock.mode', 'analog');
      expect(callback2).toHaveBeenCalledWith('clock.mode', 'analog');
    });

    it('should handle errors in subscribers gracefully', () => {
      const badCallback = vi.fn(() => {
        throw new Error('Callback error');
      });
      const goodCallback = vi.fn();

      settingsService.subscribe(badCallback);
      settingsService.subscribe(goodCallback);

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      settingsService.handleSettingUpdate({
        data: {
          key: 'clock.mode',
          value: 'analog',
        },
      });

      // Good callback should still be called
      expect(goodCallback).toHaveBeenCalled();

      consoleSpy.mockRestore();
    });
  });

  describe('Edge Cases', () => {
    it('should handle setting with various value types', () => {
      settingsService.handleSettingsResponse({
        data: {
          settings: {
            'test.string': 'value',
            'test.number': 42,
            'test.boolean': true,
          },
        },
      });

      expect(settingsService.get('test.string')).toBe('value');
      expect(settingsService.get('test.number')).toBe(42);
      expect(settingsService.get('test.boolean')).toBe(true);
    });

    it('should not call set methods without WebSocket client', async () => {
      // Don't initialize with WS client
      await settingsService.set('clock.mode', 'analog');

      // Should not crash, just return silently
    });

    it('should handle empty settings response', () => {
      settingsService.handleSettingsResponse({
        data: {
          settings: {},
        },
      });

      expect(settingsService.getAll()).toEqual({});
    });
  });
});
