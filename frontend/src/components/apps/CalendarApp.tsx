import { useState, useEffect, useCallback } from 'react';
import type { CalendarEvent, CalendarView, CreateEventData } from '../../types';
import { useWebSocket } from '../../contexts/WebSocketContext';
import { CalendarHeader } from './calendar/CalendarHeader';
import { MonthView } from './calendar/MonthView';
import { WeekView } from './calendar/WeekView';
import { DayView } from './calendar/DayView';
import { ListView } from './calendar/ListView';
import { EventModal } from './calendar/EventModal';
import '../../styles/calendar.css';

export function CalendarApp() {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [selectedDate, setSelectedDate] = useState<Date>(new Date());
  const [currentView, setCurrentView] = useState<CalendarView>('month');
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingEvent, setEditingEvent] = useState<CalendarEvent | null>(null);

  const wsClient = useWebSocket();

  // Load events on mount
  useEffect(() => {
    wsClient.sendMessage({
      type: 'calendar',
      data: { action: 'get_events' }
    });
  }, [wsClient]);

  // Listen for calendar updates
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      try {
        const message = JSON.parse(event.data);

        switch (message.type) {
          case 'calendar_events_list':
            if (message.data && Array.isArray(message.data.events)) {
              setEvents(message.data.events);
            }
            break;

          case 'calendar_event_created':
            if (message.data && message.data.event) {
              setEvents(prev => [...prev, message.data.event]);
            }
            break;

          case 'calendar_event_updated':
            if (message.data && message.data.event) {
              setEvents(prev => prev.map(e =>
                e.id === message.data.event.id ? message.data.event : e
              ));
            }
            break;

          case 'calendar_event_deleted':
            if (message.data && message.data.event_id) {
              setEvents(prev => prev.filter(e => e.id !== message.data.event_id));
            }
            break;
        }
      } catch (error) {
        console.error('Error handling calendar message:', error);
      }
    };

    wsClient.addEventListener('message', handleMessage);
    return () => wsClient.removeEventListener('message', handleMessage);
  }, [wsClient]);

  const handleCreateEvent = useCallback((eventData: CreateEventData) => {
    wsClient.sendMessage({
      type: 'calendar',
      data: {
        action: 'create_event',
        event: eventData
      }
    });
    setIsModalOpen(false);
  }, [wsClient]);

  const handleUpdateEvent = useCallback((eventId: string, updates: Partial<CalendarEvent>) => {
    wsClient.sendMessage({
      type: 'calendar',
      data: {
        action: 'update_event',
        event_id: eventId,
        updates
      }
    });
    setIsModalOpen(false);
    setEditingEvent(null);
  }, [wsClient]);

  const handleDeleteEvent = useCallback((eventId: string) => {
    wsClient.sendMessage({
      type: 'calendar',
      data: {
        action: 'delete_event',
        event_id: eventId
      }
    });
    setIsModalOpen(false);
    setEditingEvent(null);
  }, [wsClient]);

  const handleDateClick = useCallback((date: Date) => {
    setSelectedDate(date);
  }, []);

  const handleEventClick = useCallback((event: CalendarEvent) => {
    setEditingEvent(event);
    setIsModalOpen(true);
  }, []);

  const handleCreateClick = useCallback((date?: Date) => {
    if (date) {
      setSelectedDate(date);
    }
    setEditingEvent(null);
    setIsModalOpen(true);
  }, []);

  const handleEventDrop = useCallback((eventId: string, newDate: Date, newHour?: number) => {
    const event = events.find(e => e.id === eventId);
    if (!event) return;

    const oldStart = new Date(event.start_time);
    const oldEnd = new Date(event.end_time);
    const duration = oldEnd.getTime() - oldStart.getTime();

    // Create new start time with the new date and optionally new hour
    const newStart = new Date(newDate);
    if (newHour !== undefined) {
      newStart.setHours(newHour, oldStart.getMinutes(), oldStart.getSeconds());
    } else {
      newStart.setHours(oldStart.getHours(), oldStart.getMinutes(), oldStart.getSeconds());
    }

    // Calculate new end time (maintain duration)
    const newEnd = new Date(newStart.getTime() + duration);

    // Update event
    wsClient.sendMessage({
      type: 'calendar',
      data: {
        action: 'update_event',
        event_id: eventId,
        updates: {
          start_time: newStart.toISOString(),
          end_time: newEnd.toISOString()
        }
      }
    });
  }, [events, wsClient]);

  const renderView = () => {
    switch (currentView) {
      case 'month':
        return (
          <MonthView
            events={events}
            selectedDate={selectedDate}
            onDateClick={handleDateClick}
            onEventClick={handleEventClick}
            onCreateEvent={handleCreateClick}
            onEventDrop={handleEventDrop}
          />
        );

      case 'week':
        return (
          <WeekView
            events={events}
            selectedDate={selectedDate}
            onEventClick={handleEventClick}
            onTimeSlotClick={(date, hour) => {
              const newDate = new Date(date);
              newDate.setHours(hour, 0, 0, 0);
              setSelectedDate(newDate);
              handleCreateClick(newDate);
            }}
            onEventDrop={(eventId, date, hour) => handleEventDrop(eventId, date, hour)}
          />
        );

      case 'day':
        return (
          <DayView
            events={events}
            selectedDate={selectedDate}
            onEventClick={handleEventClick}
            onTimeSlotClick={(hour) => {
              const newDate = new Date(selectedDate);
              newDate.setHours(hour, 0, 0, 0);
              setSelectedDate(newDate);
              handleCreateClick(newDate);
            }}
            onEventDrop={(eventId, hour) => handleEventDrop(eventId, selectedDate, hour)}
          />
        );

      case 'list':
        return (
          <ListView
            events={events}
            onEventClick={handleEventClick}
          />
        );

      default:
        return null;
    }
  };

  return (
    <div className="calendar-app">
      <CalendarHeader
        currentView={currentView}
        selectedDate={selectedDate}
        onViewChange={setCurrentView}
        onDateChange={setSelectedDate}
        onCreateEvent={() => handleCreateClick()}
      />

      <div className="calendar-view">
        {renderView()}
      </div>

      {isModalOpen && (
        <EventModal
          event={editingEvent}
          selectedDate={selectedDate}
          onSave={editingEvent ?
            (updates) => handleUpdateEvent(editingEvent.id, updates) :
            handleCreateEvent
          }
          onDelete={editingEvent ? () => handleDeleteEvent(editingEvent.id) : undefined}
          onClose={() => {
            setIsModalOpen(false);
            setEditingEvent(null);
          }}
        />
      )}
    </div>
  );
}
