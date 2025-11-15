import { useState, useEffect, useCallback } from 'react';
import type { CalendarEvent, CalendarView, CreateEventData } from '../../types';
import { useWebSocket } from '../../contexts/WebSocketContext';
import { CalendarHeader } from './calendar/CalendarHeader';
import { MonthView } from './calendar/MonthView';
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
      const message = JSON.parse(event.data);

      switch (message.type) {
        case 'calendar_events_list':
          setEvents(message.data.events);
          break;

        case 'calendar_event_created':
          setEvents(prev => [...prev, message.data.event]);
          break;

        case 'calendar_event_updated':
          setEvents(prev => prev.map(e =>
            e.id === message.data.event.id ? message.data.event : e
          ));
          break;

        case 'calendar_event_deleted':
          setEvents(prev => prev.filter(e => e.id !== message.data.event_id));
          break;
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
          />
        );

      case 'week':
        // TODO: Implement WeekView
        return <div className="calendar-view-placeholder">Week View - Coming Soon</div>;

      case 'day':
        // TODO: Implement DayView
        return <div className="calendar-view-placeholder">Day View - Coming Soon</div>;

      case 'list':
        // TODO: Implement ListView
        return <div className="calendar-view-placeholder">List View - Coming Soon</div>;

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
