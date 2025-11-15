/**
 * Clock Widget Component
 *
 * Displays game time with configurable display modes (analog/digital/off)
 * and positioning. Syncs with the backend time service.
 */

import { useState, useEffect } from 'react';
import { timeService } from '../services/timeService';
import { settingsService } from '../services/settingsService';
import { AnalogClock } from './AnalogClock';
import { DigitalClock } from './DigitalClock';
import './ClockWidget.css';

export function ClockWidget() {
  const [currentTime, setCurrentTime] = useState(new Date());
  const [mode, setMode] = useState<string>('digital');
  const [position, setPosition] = useState<string>('top-right');
  const [format, setFormat] = useState<string>('24h');
  const [showSeconds, setShowSeconds] = useState(true);
  const [showDate, setShowDate] = useState(true);

  // Subscribe to time updates
  useEffect(() => {
    // Update time every second for smooth display
    const updateInterval = setInterval(() => {
      setCurrentTime(timeService.getCurrentTime());
    }, 1000);

    // Subscribe to time service for changes
    const unsubscribeTime = timeService.subscribe((state) => {
      setCurrentTime(state.currentTime);
    });

    return () => {
      clearInterval(updateInterval);
      unsubscribeTime();
    };
  }, []);

  // Subscribe to settings changes
  useEffect(() => {
    // Load initial settings
    setMode(settingsService.get('clock.mode') as string || 'digital');
    setPosition(settingsService.get('clock.position') as string || 'top-right');
    setFormat(settingsService.get('clock.format') as string || '24h');
    setShowSeconds(settingsService.get('clock.showSeconds') as boolean ?? true);
    setShowDate(settingsService.get('clock.showDate') as boolean ?? true);

    // Subscribe to changes
    const unsubscribeSettings = settingsService.subscribe((key, value) => {
      if (key === 'clock.mode') setMode(value as string);
      if (key === 'clock.position') setPosition(value as string);
      if (key === 'clock.format') setFormat(value as string);
      if (key === 'clock.showSeconds') setShowSeconds(value as boolean);
      if (key === 'clock.showDate') setShowDate(value as boolean);
    });

    return unsubscribeSettings;
  }, []);

  // Don't render if mode is 'off'
  if (mode === 'off') {
    return null;
  }

  return (
    <div className={`clock-widget clock-widget-${position}`}>
      {mode === 'analog' && (
        <AnalogClock time={currentTime} />
      )}
      {mode === 'digital' && (
        <DigitalClock
          time={currentTime}
          format={format}
          showSeconds={showSeconds}
          showDate={showDate}
        />
      )}
    </div>
  );
}
