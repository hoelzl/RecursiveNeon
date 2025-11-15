import { useMemo } from 'react';
import type { CalendarEvent } from '../../../types';
import { timeService } from '../../../services/timeService';

interface WeekViewProps {
  events: CalendarEvent[];
  selectedDate: Date;
  onEventClick: (event: CalendarEvent) => void;
  onTimeSlotClick: (date: Date, hour: number) => void;
  onEventDrop?: (eventId: string, newDate: Date, newHour: number) => void;
}

export function WeekView({
  events,
  selectedDate,
  onEventClick,
  onTimeSlotClick,
  onEventDrop
}: WeekViewProps) {
  const weekDays = useMemo(() => {
    const startOfWeek = new Date(selectedDate);
    const day = startOfWeek.getDay();
    const diff = startOfWeek.getDate() - day; // Adjust to Sunday
    startOfWeek.setDate(diff);
    startOfWeek.setHours(0, 0, 0, 0);

    const days: Date[] = [];
    for (let i = 0; i < 7; i++) {
      const date = new Date(startOfWeek);
      date.setDate(startOfWeek.getDate() + i);
      days.push(date);
    }
    return days;
  }, [selectedDate]);

  const hours = Array.from({ length: 24 }, (_, i) => i);

  const getEventsForTimeSlot = (date: Date, hour: number): CalendarEvent[] => {
    const slotStart = new Date(date);
    slotStart.setHours(hour, 0, 0, 0);
    const slotEnd = new Date(date);
    slotEnd.setHours(hour + 1, 0, 0, 0);

    return events.filter(event => {
      const eventStart = new Date(event.start_time);
      const eventEnd = new Date(event.end_time);
      const eventDate = eventStart.toDateString();
      const slotDate = date.toDateString();

      // Check if event is on this day
      if (eventDate !== slotDate) {
        // Check for multi-day events
        const dateOnly = new Date(date);
        dateOnly.setHours(0, 0, 0, 0);
        const eventStartDate = new Date(eventStart);
        eventStartDate.setHours(0, 0, 0, 0);
        const eventEndDate = new Date(eventEnd);
        eventEndDate.setHours(0, 0, 0, 0);

        if (dateOnly < eventStartDate || dateOnly > eventEndDate) {
          return false;
        }
      }

      // All day events
      if (event.all_day) {
        return hour === 0; // Show at midnight
      }

      // Check if event overlaps with this hour slot
      return eventStart < slotEnd && eventEnd > slotStart;
    });
  };

  const isToday = (date: Date): boolean => {
    const today = timeService.getCurrentTime();
    return date.toDateString() === today.toDateString();
  };

  const formatHour = (hour: number): string => {
    if (hour === 0) return '12 AM';
    if (hour < 12) return `${hour} AM`;
    if (hour === 12) return '12 PM';
    return `${hour - 12} PM`;
  };

  const getEventPosition = (event: CalendarEvent, hour: number): { top: string; height: string } => {
    const eventStart = new Date(event.start_time);
    const eventEnd = new Date(event.end_time);

    const startHour = eventStart.getHours();
    const startMinute = eventStart.getMinutes();
    const endHour = eventEnd.getHours();
    const endMinute = eventEnd.getMinutes();

    const startOffset = ((startHour - hour) * 60 + startMinute) / 60 * 100;
    const duration = ((endHour - startHour) * 60 + (endMinute - startMinute)) / 60 * 100;

    return {
      top: `${Math.max(0, startOffset)}%`,
      height: `${Math.max(10, duration)}%`
    };
  };

  const handleDragStart = (e: React.DragEvent, event: CalendarEvent) => {
    e.stopPropagation();
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', event.id);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = (e: React.DragEvent, date: Date, hour: number) => {
    e.preventDefault();
    e.stopPropagation();

    const eventId = e.dataTransfer.getData('text/plain');
    if (eventId && onEventDrop) {
      onEventDrop(eventId, date, hour);
    }
  };

  return (
    <div className="week-view">
      <div className="week-grid">
        {/* Time column header */}
        <div className="time-header"></div>

        {/* Day headers */}
        {weekDays.map((date, index) => (
          <div key={index} className={`week-day-header ${isToday(date) ? 'today' : ''}`}>
            <div className="day-name">
              {date.toLocaleDateString('en-US', { weekday: 'short' })}
            </div>
            <div className="day-date">
              {date.getDate()}
            </div>
          </div>
        ))}

        {/* Time slots */}
        {hours.map(hour => (
          <>
            {/* Hour label */}
            <div key={`hour-${hour}`} className="hour-label">
              {formatHour(hour)}
            </div>

            {/* Day columns for this hour */}
            {weekDays.map((date, dayIndex) => {
              const slotEvents = getEventsForTimeSlot(date, hour);

              return (
                <div
                  key={`${hour}-${dayIndex}`}
                  className={`time-slot ${isToday(date) ? 'today' : ''}`}
                  onClick={() => onTimeSlotClick(date, hour)}
                  onDragOver={handleDragOver}
                  onDrop={(e) => handleDrop(e, date, hour)}
                >
                  {slotEvents.map(event => {
                    const position = getEventPosition(event, hour);
                    return (
                      <div
                        key={event.id}
                        className="week-event"
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
                        title={`${event.title}\n${new Date(event.start_time).toLocaleTimeString()} - ${new Date(event.end_time).toLocaleTimeString()}`}
                      >
                        <div className="event-title">{event.title}</div>
                        {!event.all_day && (
                          <div className="event-time-range">
                            {new Date(event.start_time).toLocaleTimeString('en-US', {
                              hour: 'numeric',
                              minute: '2-digit'
                            })}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              );
            })}
          </>
        ))}
      </div>
    </div>
  );
}
