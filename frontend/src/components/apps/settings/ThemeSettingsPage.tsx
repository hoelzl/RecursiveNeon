/**
 * Theme Settings Page
 *
 * Configuration page for selecting and previewing themes.
 */

import { useState, useEffect } from 'react';
import { settingsService } from '../../../services/settingsService';
import { themes, applyTheme } from '../../../themes/themes';
import './SettingsPages.css';

export function ThemeSettingsPage() {
  const [currentTheme, setCurrentTheme] = useState<string>('classic');

  // Load current theme
  useEffect(() => {
    const theme = settingsService.get('theme.current') as string || 'classic';
    setCurrentTheme(theme);
    applyTheme(theme);

    const unsubscribe = settingsService.subscribe((key, value) => {
      if (key === 'theme.current') {
        setCurrentTheme(value as string);
        applyTheme(value as string);
      }
    });

    return unsubscribe;
  }, []);

  const handleThemeChange = (themeId: string) => {
    setCurrentTheme(themeId);
    settingsService.set('theme.current', themeId);
    applyTheme(themeId);
  };

  return (
    <div className="settings-page">
      <h2>Theme Settings</h2>
      <p className="settings-page-description">
        Choose a visual theme for the desktop environment.
      </p>

      <div className="setting-group">
        <h3>Available Themes</h3>
        <div className="theme-grid">
          {themes.map((theme) => (
            <div
              key={theme.id}
              className={`theme-card ${currentTheme === theme.id ? 'selected' : ''}`}
              onClick={() => handleThemeChange(theme.id)}
            >
              <div className="theme-preview">
                {/* Color swatches */}
                <div className="theme-colors">
                  <div
                    className="theme-color-swatch"
                    style={{ background: theme.colors.background }}
                    title="Background"
                  />
                  <div
                    className="theme-color-swatch"
                    style={{ background: theme.colors.surface }}
                    title="Surface"
                  />
                  <div
                    className="theme-color-swatch"
                    style={{ background: theme.colors.accent }}
                    title="Accent"
                  />
                  <div
                    className="theme-color-swatch"
                    style={{ background: theme.colors.text }}
                    title="Text"
                  />
                </div>
              </div>
              <div className="theme-info">
                <div className="theme-name">{theme.name}</div>
                <div className="theme-description">{theme.description}</div>
              </div>
              {currentTheme === theme.id && (
                <div className="theme-selected-badge">✓ Active</div>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="setting-group">
        <h3>Current Theme Details</h3>
        {themes.find(t => t.id === currentTheme) && (
          <div className="theme-details">
            <p><strong>Name:</strong> {themes.find(t => t.id === currentTheme)!.name}</p>
            <p><strong>Description:</strong> {themes.find(t => t.id === currentTheme)!.description}</p>
          </div>
        )}
      </div>
    </div>
  );
}
