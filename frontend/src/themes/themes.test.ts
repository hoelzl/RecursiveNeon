/**
 * Tests for Theme System
 *
 * Tests theme definitions and application.
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { themes, getTheme, applyTheme } from './themes';

describe('Theme System', () => {
  describe('Theme Definitions', () => {
    it('should have at least 6 themes defined', () => {
      expect(themes.length).toBeGreaterThanOrEqual(6);
    });

    it('should have unique theme IDs', () => {
      const ids = themes.map(t => t.id);
      const uniqueIds = new Set(ids);

      expect(ids.length).toBe(uniqueIds.size);
    });

    it('should have all required theme properties', () => {
      themes.forEach(theme => {
        expect(theme.id).toBeTruthy();
        expect(theme.name).toBeTruthy();
        expect(theme.description).toBeTruthy();
        expect(theme.colors).toBeDefined();

        // Check all required color properties
        expect(theme.colors.primary).toBeTruthy();
        expect(theme.colors.secondary).toBeTruthy();
        expect(theme.colors.background).toBeTruthy();
        expect(theme.colors.surface).toBeTruthy();
        expect(theme.colors.text).toBeTruthy();
        expect(theme.colors.textSecondary).toBeTruthy();
        expect(theme.colors.border).toBeTruthy();
        expect(theme.colors.accent).toBeTruthy();
        expect(theme.colors.success).toBeTruthy();
        expect(theme.colors.warning).toBeTruthy();
        expect(theme.colors.error).toBeTruthy();
        expect(theme.colors.taskbarBackground).toBeTruthy();
        expect(theme.colors.windowTitleBar).toBeTruthy();
      });
    });

    it('should have expected default themes', () => {
      const themeIds = themes.map(t => t.id);

      expect(themeIds).toContain('classic');
      expect(themeIds).toContain('dark');
      expect(themeIds).toContain('light');
      expect(themeIds).toContain('neon');
      expect(themeIds).toContain('terminal');
      expect(themeIds).toContain('cyberpunk');
    });

    it('should have valid hex color values', () => {
      const hexColorRegex = /^#[0-9A-Fa-f]{6}$/;

      themes.forEach(theme => {
        Object.values(theme.colors).forEach(color => {
          expect(color).toMatch(hexColorRegex);
        });
      });
    });
  });

  describe('getTheme', () => {
    it('should return theme by ID', () => {
      const theme = getTheme('classic');

      expect(theme).toBeDefined();
      expect(theme?.id).toBe('classic');
      expect(theme?.name).toBe('Classic');
    });

    it('should return undefined for nonexistent theme', () => {
      const theme = getTheme('nonexistent');

      expect(theme).toBeUndefined();
    });

    it('should return correct theme for each ID', () => {
      themes.forEach(expectedTheme => {
        const theme = getTheme(expectedTheme.id);

        expect(theme).toEqual(expectedTheme);
      });
    });
  });

  describe('applyTheme', () => {
    beforeEach(() => {
      // Clear any existing CSS variables
      document.documentElement.style.cssText = '';
    });

    afterEach(() => {
      // Clean up
      document.documentElement.style.cssText = '';
    });

    it('should apply theme CSS variables', () => {
      applyTheme('classic');

      const root = document.documentElement;
      const classicTheme = getTheme('classic')!;

      expect(root.style.getPropertyValue('--primary')).toBe(classicTheme.colors.primary);
      expect(root.style.getPropertyValue('--background')).toBe(classicTheme.colors.background);
      expect(root.style.getPropertyValue('--accent')).toBe(classicTheme.colors.accent);
    });

    it('should apply all color properties', () => {
      applyTheme('dark');

      const root = document.documentElement;
      const darkTheme = getTheme('dark')!;

      Object.entries(darkTheme.colors).forEach(([key, value]) => {
        const cssVarName = `--${key.replace(/([a-z])([A-Z])/g, '$1-$2').toLowerCase()}`;
        expect(root.style.getPropertyValue(cssVarName)).toBe(value);
      });
    });

    it('should handle nonexistent theme gracefully', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      applyTheme('nonexistent');

      expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('not found'));

      consoleSpy.mockRestore();
    });

    it('should be able to switch themes', () => {
      applyTheme('classic');

      let root = document.documentElement;
      let classicAccent = getTheme('classic')!.colors.accent;

      expect(root.style.getPropertyValue('--accent')).toBe(classicAccent);

      applyTheme('neon');

      root = document.documentElement;
      let neonAccent = getTheme('neon')!.colors.accent;

      expect(root.style.getPropertyValue('--accent')).toBe(neonAccent);
    });

    it('should convert camelCase to kebab-case correctly', () => {
      applyTheme('dark');

      const root = document.documentElement;

      // textSecondary should become --text-secondary
      expect(root.style.getPropertyValue('--text-secondary')).toBeTruthy();

      // taskbarBackground should become --taskbar-background
      expect(root.style.getPropertyValue('--taskbar-background')).toBeTruthy();

      // windowTitleBar should become --window-title-bar
      expect(root.style.getPropertyValue('--window-title-bar')).toBeTruthy();
    });
  });

  describe('Theme Characteristics', () => {
    it('classic theme should have cyan accent', () => {
      const classic = getTheme('classic')!;

      expect(classic.colors.accent.toLowerCase()).toContain('00d4ff');
    });

    it('dark theme should have dark background', () => {
      const dark = getTheme('dark')!;

      // Dark backgrounds should have low RGB values
      const bgColor = dark.colors.background;
      const rgb = parseInt(bgColor.slice(1), 16);

      expect(rgb).toBeLessThan(0x404040);
    });

    it('light theme should have light background', () => {
      const light = getTheme('light')!;

      // Light backgrounds should have high RGB values
      const bgColor = light.colors.background;
      const rgb = parseInt(bgColor.slice(1), 16);

      expect(rgb).toBeGreaterThan(0xE0E0E0);
    });

    it('terminal theme should have green colors', () => {
      const terminal = getTheme('terminal')!;

      // Should have green (00FF00 or similar)
      expect(terminal.colors.text.toLowerCase()).toContain('00ff00');
    });
  });
});
