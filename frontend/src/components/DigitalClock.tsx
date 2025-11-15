/**
 * Digital Clock Component
 *
 * Displays a digital clock with configurable format and options.
 */

import './DigitalClock.css';

interface DigitalClockProps {
  time: Date;
  format: string;
  showSeconds: boolean;
  showDate: boolean;
}

export function DigitalClock({ time, format, showSeconds, showDate }: DigitalClockProps) {
  const formatTime = (date: Date): string => {
    let hours = date.getHours();
    const minutes = date.getMinutes();
    const seconds = date.getSeconds();
    let period = '';

    if (format === '12h') {
      period = hours >= 12 ? ' PM' : ' AM';
      hours = hours % 12 || 12;
    }

    const hoursStr = String(hours).padStart(2, '0');
    const minutesStr = String(minutes).padStart(2, '0');
    const secondsStr = String(seconds).padStart(2, '0');

    let timeStr = `${hoursStr}:${minutesStr}`;
    if (showSeconds) {
      timeStr += `:${secondsStr}`;
    }
    timeStr += period;

    return timeStr;
  };

  const formatDate = (date: Date): string => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  return (
    <div className="digital-clock">
      <div className="digital-clock-time">{formatTime(time)}</div>
      {showDate && (
        <div className="digital-clock-date">{formatDate(time)}</div>
      )}
    </div>
  );
}
