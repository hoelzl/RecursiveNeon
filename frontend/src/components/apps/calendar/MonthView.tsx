import { useMemo } from 'react';
import type { CalendarEvent } from '../../../types';
import { timeService } from '../../../services/timeService';

interface MonthViewProps {
  events: CalendarEvent[];
  selectedDate: Date;
  onDateClick: (date: Date) => void;
  onEventClick: (event: CalendarEvent) => void;
  onCreateEvent: (date: Date) => void;
  onEventDrop?: (eventId: string, newDate: Date) => void;
}

export function MonthView({
  events,
  selectedDate,
  onDateClick,
  onEventClick,
  onCreateEvent,
  onEventDrop
}: MonthViewProps) {
  const monthDays = useMemo(() => {
    const year = selectedDate.getFullYear();
    const month = selectedDate.getMonth();

    // Get first day of month
    const firstDay = new Date(year, month, 1);
    const firstDayOfWeek = firstDay.getDay(); // 0 = Sunday

    // Get last day of month
    const lastDay = new Date(year, month + 1, 0);
    const totalDays = lastDay.getDate();

    // Calculate days to show (including leading/trailing days from adjacent months)
    const days: Date[] = [];

    // Add trailing days from previous month
    const prevMonthLastDay = new Date(year, month, 0).getDate();
    for (let i = firstDayOfWeek - 1; i >= 0; i--) {
      days.push(new Date(year, month - 1, prevMonthLastDay - i));
    }

    // Add current month days
    for (let day = 1; day <= totalDays; day++) {
      days.push(new Date(year, month, day));
    }

    // Add leading days from next month to complete the grid
    const remainingDays = 42 - days.length; // 6 weeks * 7 days
    for (let day = 1; day <= remainingDays; day++) {
      days.push(new Date(year, month + 1, day));
    }

    return days;
  }, [selectedDate]);

  const getEventsForDate = (date: Date): CalendarEvent[] => {
    const dateStr = date.toISOString().split('T')[0];

    return events.filter(event => {
      const eventStart = new Date(event.start_time);
      const eventEnd = new Date(event.end_time);
      const eventStartStr = eventStart.toISOString().split('T')[0];
      const eventEndStr = eventEnd.toISOString().split('T')[0];

      return dateStr >= eventStartStr && dateStr <= eventEndStr;
    });
  };

  const isToday = (date: Date): boolean => {
    const today = timeService.getCurrentTime();
    return date.toDateString() === today.toDateString();
  };

  const isCurrentMonth = (date: Date): boolean => {
    return date.getMonth() === selectedDate.getMonth();
  };

  const handleDayClick = (date: Date) => {
    onDateClick(date);
  };

  const handleDayDoubleClick = (date: Date) => {
    onCreateEvent(date);
  };

  const handleDragStart = (e: React.DragEvent, event: CalendarEvent) => {
    e.stopPropagation();
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('eventId', event.id);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = (e: React.DragEvent, date: Date) => {
    e.preventDefault();
    e.stopPropagation();

    const eventId = e.dataTransfer.getData('eventId');
    if (eventId && onEventDrop) {
      onEventDrop(eventId, date);
    }
  };

  return (
    <div className="month-view">
      <div className="month-grid">
        {/* Day headers */}
        <div className="day-header">Sun</div>
        <div className="day-header">Mon</div>
        <div className="day-header">Tue</div>
        <div className="day-header">Wed</div>
        <div className="day-header">Thu</div>
        <div className="day-header">Fri</div>
        <div className="day-header">Sat</div>

        {/* Day cells */}
        {monthDays.map((date, index) => {
          const dayEvents = getEventsForDate(date);
          const isTodayDate = isToday(date);
          const isCurrentMonthDate = isCurrentMonth(date);

          return (
            <div
              key={index}
              className={`day-cell ${!isCurrentMonthDate ? 'other-month' : ''} ${isTodayDate ? 'today' : ''}`}
              onClick={() => handleDayClick(date)}
              onDoubleClick={() => handleDayDoubleClick(date)}
              onDragOver={handleDragOver}
              onDrop={(e) => handleDrop(e, date)}
            >
              <div className="day-number">{date.getDate()}</div>
              <div className="day-events">
                {dayEvents.slice(0, 3).map(event => (
                  <div
                    key={event.id}
                    className="event-pill"
                    style={{ backgroundColor: event.color || '#4A90E2' }}
                    draggable={!!onEventDrop}
                    onDragStart={(e) => handleDragStart(e, event)}
                    onClick={(e) => {
                      e.stopPropagation();
                      onEventClick(event);
                    }}
                    title={event.title}
                  >
                    <span className="event-time">
                      {event.all_day ? 'All day' : new Date(event.start_time).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}
                    </span>
                    <span className="event-title">{event.title}</span>
                  </div>
                ))}
                {dayEvents.length > 3 && (
                  <div className="event-more">
                    +{dayEvents.length - 3} more
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
