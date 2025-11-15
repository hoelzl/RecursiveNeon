/**
 * Analog Clock Component
 *
 * Displays an analog clock face with hour, minute, and second hands.
 */

import './AnalogClock.css';

interface AnalogClockProps {
  time: Date;
}

export function AnalogClock({ time }: AnalogClockProps) {
  const hours = time.getHours() % 12;
  const minutes = time.getMinutes();
  const seconds = time.getSeconds();

  // Calculate rotation angles
  const secondAngle = (seconds / 60) * 360;
  const minuteAngle = (minutes / 60) * 360 + (seconds / 60) * 6;
  const hourAngle = (hours / 12) * 360 + (minutes / 60) * 30;

  return (
    <div className="analog-clock">
      <div className="analog-clock-face">
        {/* Hour markers */}
        {[...Array(12)].map((_, i) => (
          <div
            key={i}
            className="hour-marker"
            style={{
              transform: `rotate(${i * 30}deg) translateY(-35px)`,
            }}
          >
            <div style={{ transform: `rotate(-${i * 30}deg)` }}>
              {i === 0 ? 12 : i}
            </div>
          </div>
        ))}

        {/* Clock hands */}
        <div
          className="clock-hand hour-hand"
          style={{ transform: `rotate(${hourAngle}deg)` }}
        />
        <div
          className="clock-hand minute-hand"
          style={{ transform: `rotate(${minuteAngle}deg)` }}
        />
        <div
          className="clock-hand second-hand"
          style={{ transform: `rotate(${secondAngle}deg)` }}
        />

        {/* Center dot */}
        <div className="clock-center" />
      </div>
    </div>
  );
}
