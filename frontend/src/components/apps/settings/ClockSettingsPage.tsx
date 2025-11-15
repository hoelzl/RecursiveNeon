/**
 * Clock Settings Page
 *
 * Configuration page for clock widget settings.
 */

import { useState, useEffect } from 'react';
import { settingsService } from '../../../services/settingsService';
import './SettingsPages.css';

export function ClockSettingsPage() {
  const [mode, setMode] = useState<string>('digital');
  const [position, setPosition] = useState<string>('top-right');
  const [format, setFormat] = useState<string>('24h');
  const [showSeconds, setShowSeconds] = useState(true);
  const [showDate, setShowDate] = useState(true);

  // Load current settings
  useEffect(() => {
    setMode(settingsService.get('clock.mode') as string || 'digital');
    setPosition(settingsService.get('clock.position') as string || 'top-right');
    setFormat(settingsService.get('clock.format') as string || '24h');
    setShowSeconds(settingsService.get('clock.showSeconds') as boolean ?? true);
    setShowDate(settingsService.get('clock.showDate') as boolean ?? true);

    const unsubscribe = settingsService.subscribe((key, value) => {
      if (key === 'clock.mode') setMode(value as string);
      if (key === 'clock.position') setPosition(value as string);
      if (key === 'clock.format') setFormat(value as string);
      if (key === 'clock.showSeconds') setShowSeconds(value as boolean);
      if (key === 'clock.showDate') setShowDate(value as boolean);
    });

    return unsubscribe;
  }, []);

  const handleModeChange = (newMode: string) => {
    setMode(newMode);
    settingsService.set('clock.mode', newMode);
  };

  const handlePositionChange = (newPosition: string) => {
    setPosition(newPosition);
    settingsService.set('clock.position', newPosition);
  };

  const handleFormatChange = (newFormat: string) => {
    setFormat(newFormat);
    settingsService.set('clock.format', newFormat);
  };

  const handleShowSecondsChange = (show: boolean) => {
    setShowSeconds(show);
    settingsService.set('clock.showSeconds', show);
  };

  const handleShowDateChange = (show: boolean) => {
    setShowDate(show);
    settingsService.set('clock.showDate', show);
  };

  const resetToDefaults = () => {
    settingsService.reset('clock.mode');
    settingsService.reset('clock.position');
    settingsService.reset('clock.format');
    settingsService.reset('clock.showSeconds');
    settingsService.reset('clock.showDate');
  };

  return (
    <div className="settings-page">
      <h2>Clock Settings</h2>
      <p className="settings-page-description">
        Configure the appearance and behavior of the clock widget.
      </p>

      <div className="setting-group">
        <h3>Display Mode</h3>
        <div className="radio-group">
          <label className="radio-label">
            <input
              type="radio"
              name="clock-mode"
              value="off"
              checked={mode === 'off'}
              onChange={(e) => handleModeChange(e.target.value)}
            />
            <span>Hidden</span>
          </label>
          <label className="radio-label">
            <input
              type="radio"
              name="clock-mode"
              value="analog"
              checked={mode === 'analog'}
              onChange={(e) => handleModeChange(e.target.value)}
            />
            <span>Analog</span>
          </label>
          <label className="radio-label">
            <input
              type="radio"
              name="clock-mode"
              value="digital"
              checked={mode === 'digital'}
              onChange={(e) => handleModeChange(e.target.value)}
            />
            <span>Digital</span>
          </label>
        </div>
      </div>

      <div className="setting-group">
        <h3>Position</h3>
        <select
          className="settings-select"
          value={position}
          onChange={(e) => handlePositionChange(e.target.value)}
        >
          <option value="top-left">Top Left</option>
          <option value="top-right">Top Right</option>
          <option value="bottom-left">Bottom Left</option>
          <option value="bottom-right">Bottom Right</option>
        </select>
      </div>

      {mode === 'digital' && (
        <>
          <div className="setting-group">
            <h3>Digital Clock Options</h3>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={showSeconds}
                onChange={(e) => handleShowSecondsChange(e.target.checked)}
              />
              <span>Show seconds</span>
            </label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={showDate}
                onChange={(e) => handleShowDateChange(e.target.checked)}
              />
              <span>Show date</span>
            </label>
          </div>

          <div className="setting-group">
            <h3>Time Format</h3>
            <div className="radio-group">
              <label className="radio-label">
                <input
                  type="radio"
                  name="clock-format"
                  value="12h"
                  checked={format === '12h'}
                  onChange={(e) => handleFormatChange(e.target.value)}
                />
                <span>12-hour (AM/PM)</span>
              </label>
              <label className="radio-label">
                <input
                  type="radio"
                  name="clock-format"
                  value="24h"
                  checked={format === '24h'}
                  onChange={(e) => handleFormatChange(e.target.value)}
                />
                <span>24-hour</span>
              </label>
            </div>
          </div>
        </>
      )}

      <div className="setting-actions">
        <button className="settings-button" onClick={resetToDefaults}>
          Reset to Defaults
        </button>
      </div>
    </div>
  );
}
