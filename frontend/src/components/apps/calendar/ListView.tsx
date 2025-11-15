import { useMemo } from 'react';
import type { CalendarEvent } from '../../../types';

interface ListViewProps {
  events: CalendarEvent[];
  onEventClick: (event: CalendarEvent) => void;
}

export function ListView({ events, onEventClick }: ListViewProps) {
  const groupedEvents = useMemo(() => {
    // Sort events by start time
    const sortedEvents = [...events].sort((a, b) => {
      return new Date(a.start_time).getTime() - new Date(b.start_time).getTime();
    });

    // Group by date
    const groups: Map<string, CalendarEvent[]> = new Map();

    sortedEvents.forEach(event => {
      const eventDate = new Date(event.start_time);
      const dateKey = eventDate.toDateString();

      if (!groups.has(dateKey)) {
        groups.set(dateKey, []);
      }
      groups.get(dateKey)!.push(event);
    });

    return Array.from(groups.entries()).map(([dateStr, dateEvents]) => ({
      date: new Date(dateStr),
      events: dateEvents
    }));
  }, [events]);

  const formatDate = (date: Date): string => {
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);

    if (date.toDateString() === today.toDateString()) {
      return 'Today';
    } else if (date.toDateString() === tomorrow.toDateString()) {
      return 'Tomorrow';
    } else {
      return date.toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
    }
  };

  const formatTime = (event: CalendarEvent): string => {
    if (event.all_day) {
      return 'All day';
    }

    const start = new Date(event.start_time);
    const end = new Date(event.end_time);

    return `${start.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit'
    })} - ${end.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit'
    })}`;
  };

  const isToday = (date: Date): boolean => {
    return date.toDateString() === new Date().toDateString();
  };

  const isPast = (event: CalendarEvent): boolean => {
    return new Date(event.end_time) < new Date();
  };

  if (groupedEvents.length === 0) {
    return (
      <div className="list-view-empty">
        <div className="empty-icon">📅</div>
        <div className="empty-message">No events scheduled</div>
        <div className="empty-hint">Click the "+" button to create your first event</div>
      </div>
    );
  }

  return (
    <div className="list-view">
      {groupedEvents.map(({ date, events: dateEvents }, groupIndex) => (
        <div key={groupIndex} className="list-group">
          <div className={`list-group-header ${isToday(date) ? 'today' : ''}`}>
            <div className="date-label">{formatDate(date)}</div>
            <div className="event-count-badge">
              {dateEvents.length} event{dateEvents.length !== 1 ? 's' : ''}
            </div>
          </div>

          <div className="list-group-events">
            {dateEvents.map(event => (
              <div
                key={event.id}
                className={`list-event ${isPast(event) ? 'past' : ''}`}
                onClick={() => onEventClick(event)}
              >
                <div
                  className="event-color-bar"
                  style={{ backgroundColor: event.color || '#4A90E2' }}
                />

                <div className="event-details">
                  <div className="event-header">
                    <div className="event-title">{event.title}</div>
                    <div className="event-time">{formatTime(event)}</div>
                  </div>

                  {event.description && (
                    <div className="event-description">{event.description}</div>
                  )}

                  <div className="event-meta">
                    {event.location && (
                      <div className="event-location">
                        <span className="icon">📍</span>
                        {event.location}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
