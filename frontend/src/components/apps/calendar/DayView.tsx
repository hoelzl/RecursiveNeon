import { useMemo } from 'react';
import type { CalendarEvent } from '../../../types';

interface DayViewProps {
  events: CalendarEvent[];
  selectedDate: Date;
  onEventClick: (event: CalendarEvent) => void;
  onTimeSlotClick: (hour: number) => void;
  onEventDrop?: (eventId: string, newHour: number) => void;
}

export function DayView({
  events,
  selectedDate,
  onEventClick,
  onTimeSlotClick,
  onEventDrop
}: DayViewProps) {
  const hours = Array.from({ length: 24 }, (_, i) => i);

  const dayEvents = useMemo(() => {
    const dateStr = selectedDate.toDateString();

    return events.filter(event => {
      const eventStart = new Date(event.start_time);
      const eventEnd = new Date(event.end_time);
      const eventStartStr = eventStart.toDateString();
      const eventEndStr = eventEnd.toDateString();

      // Event falls on this day
      return dateStr >= eventStartStr && dateStr <= eventEndStr;
    });
  }, [events, selectedDate]);

  const getEventsForHour = (hour: number): CalendarEvent[] => {
    const hourStart = new Date(selectedDate);
    hourStart.setHours(hour, 0, 0, 0);
    const hourEnd = new Date(selectedDate);
    hourEnd.setHours(hour + 1, 0, 0, 0);

    return dayEvents.filter(event => {
      if (event.all_day) {
        return hour === 0; // Show all-day events at midnight
      }

      const eventStart = new Date(event.start_time);
      const eventEnd = new Date(event.end_time);

      return eventStart < hourEnd && eventEnd > hourStart;
    });
  };

  const formatHour = (hour: number): string => {
    if (hour === 0) return '12:00 AM';
    if (hour < 12) return `${hour}:00 AM`;
    if (hour === 12) return '12:00 PM';
    return `${hour - 12}:00 PM`;
  };

  const getEventPosition = (event: CalendarEvent, hour: number): { top: string; height: string } => {
    const eventStart = new Date(event.start_time);
    const eventEnd = new Date(event.end_time);

    const startHour = eventStart.getHours();
    const startMinute = eventStart.getMinutes();
    const endHour = eventEnd.getHours();
    const endMinute = eventEnd.getMinutes();

    // Calculate position within the hour slot
    const startOffset = ((startHour - hour) * 60 + startMinute) / 60 * 100;
    const duration = ((endHour - startHour) * 60 + (endMinute - startMinute)) / 60 * 100;

    return {
      top: `${Math.max(0, startOffset)}%`,
      height: `${Math.max(10, duration)}%`
    };
  };

  const isToday = selectedDate.toDateString() === new Date().toDateString();

  const handleDragStart = (e: React.DragEvent, event: CalendarEvent) => {
    e.stopPropagation();
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('eventId', event.id);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = (e: React.DragEvent, hour: number) => {
    e.preventDefault();
    e.stopPropagation();

    const eventId = e.dataTransfer.getData('eventId');
    if (eventId && onEventDrop) {
      onEventDrop(eventId, hour);
    }
  };

  return (
    <div className="day-view">
      <div className="day-view-header">
        <h3 className={isToday ? 'today' : ''}>
          {selectedDate.toLocaleDateString('en-US', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
          })}
        </h3>
        {dayEvents.length > 0 && (
          <div className="event-count">
            {dayEvents.length} event{dayEvents.length !== 1 ? 's' : ''}
          </div>
        )}
      </div>

      <div className="day-timeline">
        {hours.map(hour => {
          const hourEvents = getEventsForHour(hour);

          return (
            <div key={hour} className="hour-slot">
              <div className="hour-label">
                {formatHour(hour)}
              </div>
              <div
                className={`hour-content ${isToday ? 'today' : ''}`}
                onClick={() => onTimeSlotClick(hour)}
                onDragOver={handleDragOver}
                onDrop={(e) => handleDrop(e, hour)}
              >
                {hourEvents.map(event => {
                  const position = getEventPosition(event, hour);
                  return (
                    <div
                      key={event.id}
                      className="day-event"
                      style={{
                        backgroundColor: event.color || '#4A90E2',
                        top: position.top,
                        height: position.height
                      }}
                      draggable={!!onEventDrop}
                      onDragStart={(e) => handleDragStart(e, event)}
                      onClick={(e) => {
                        e.stopPropagation();
                        onEventClick(event);
                      }}
                    >
                      <div className="event-title">{event.title}</div>
                      {!event.all_day && (
                        <div className="event-time-range">
                          {new Date(event.start_time).toLocaleTimeString('en-US', {
                            hour: 'numeric',
                            minute: '2-digit'
                          })}
                          {' - '}
                          {new Date(event.end_time).toLocaleTimeString('en-US', {
                            hour: 'numeric',
                            minute: '2-digit'
                          })}
                        </div>
                      )}
                      {event.location && (
                        <div className="event-location">📍 {event.location}</div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
