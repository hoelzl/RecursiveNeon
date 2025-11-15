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
  const [error, setError] = useState<string | null>(null);

  const wsClient = useWebSocket();

  // Debug logging
  useEffect(() => {
    console.log('[CalendarApp] Component mounted', { wsClient: !!wsClient });
    return () => {
      console.log('[CalendarApp] Component unmounting');
    };
  }, []);

  // Validate wsClient
  useEffect(() => {
    if (!wsClient) {
      console.error('[CalendarApp] WebSocket client is null or undefined');
      setError('WebSocket connection not available');
      return;
    }
    console.log('[CalendarApp] WebSocket client validated');
  }, [wsClient]);

  // Load events on mount
  useEffect(() => {
    if (!wsClient) {
      console.warn('[CalendarApp] Cannot load events: wsClient is null');
      return;
    }

    try {
      console.log('[CalendarApp] Requesting events from server');
      wsClient.sendMessage({
        type: 'calendar',
        data: { action: 'get_events' }
      });
    } catch (error) {
      console.error('[CalendarApp] Error requesting events:', error);
      setError('Failed to load events');
    }
  }, [wsClient]);

  // Listen for calendar updates
  useEffect(() => {
    if (!wsClient) {
      console.warn('[CalendarApp] Cannot setup message listener: wsClient is null');
      return;
    }

    const handleMessage = (event: MessageEvent) => {
      try {
        const message = JSON.parse(event.data);
        console.log('[CalendarApp] Received message:', message.type);

        switch (message.type) {
          case 'calendar_events_list':
            if (message.data && Array.isArray(message.data.events)) {
              console.log('[CalendarApp] Loaded events:', message.data.events.length);
              setEvents(message.data.events);
            }
            break;

          case 'calendar_event_created':
            if (message.data && message.data.event) {
              console.log('[CalendarApp] Event created:', message.data.event.id);
              setEvents(prev => [...prev, message.data.event]);
            }
            break;

          case 'calendar_event_updated':
            if (message.data && message.data.event) {
              console.log('[CalendarApp] Event updated:', message.data.event.id);
              setEvents(prev => prev.map(e =>
                e.id === message.data.event.id ? message.data.event : e
              ));
            }
            break;

          case 'calendar_event_deleted':
            if (message.data && message.data.event_id) {
              console.log('[CalendarApp] Event deleted:', message.data.event_id);
              setEvents(prev => prev.filter(e => e.id !== message.data.event_id));
            }
            break;
        }
      } catch (error) {
        console.error('[CalendarApp] Error handling calendar message:', error);
        setError('Error processing calendar data');
      }
    };

    try {
      console.log('[CalendarApp] Adding message event listener');
      wsClient.addEventListener('message', handleMessage);
      return () => {
        console.log('[CalendarApp] Removing message event listener');
        try {
          wsClient.removeEventListener('message', handleMessage);
        } catch (error) {
          console.error('[CalendarApp] Error removing event listener:', error);
        }
      };
    } catch (error) {
      console.error('[CalendarApp] Error setting up message listener:', error);
      setError('Failed to setup message listener');
    }
  }, [wsClient]);

  const handleCreateEvent = useCallback((eventData: CreateEventData) => {
    if (!wsClient) {
      console.error('[CalendarApp] Cannot create event: wsClient is null');
      setError('Cannot create event: No connection');
      return;
    }

    try {
      console.log('[CalendarApp] Creating event:', eventData.title);
      wsClient.sendMessage({
        type: 'calendar',
        data: {
          action: 'create_event',
          event: eventData
        }
      });
      setIsModalOpen(false);
    } catch (error) {
      console.error('[CalendarApp] Error creating event:', error);
      setError('Failed to create event');
    }
  }, [wsClient]);

  const handleUpdateEvent = useCallback((eventId: string, updates: Partial<CalendarEvent>) => {
    if (!wsClient) {
      console.error('[CalendarApp] Cannot update event: wsClient is null');
      setError('Cannot update event: No connection');
      return;
    }

    try {
      console.log('[CalendarApp] Updating event:', eventId);
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
    } catch (error) {
      console.error('[CalendarApp] Error updating event:', error);
      setError('Failed to update event');
    }
  }, [wsClient]);

  const handleDeleteEvent = useCallback((eventId: string) => {
    if (!wsClient) {
      console.error('[CalendarApp] Cannot delete event: wsClient is null');
      setError('Cannot delete event: No connection');
      return;
    }

    try {
      console.log('[CalendarApp] Deleting event:', eventId);
      wsClient.sendMessage({
        type: 'calendar',
        data: {
          action: 'delete_event',
          event_id: eventId
        }
      });
      setIsModalOpen(false);
      setEditingEvent(null);
    } catch (error) {
      console.error('[CalendarApp] Error deleting event:', error);
      setError('Failed to delete event');
    }
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
    if (!wsClient) {
      console.error('[CalendarApp] Cannot move event: wsClient is null');
      setError('Cannot move event: No connection');
      return;
    }

    const event = events.find(e => e.id === eventId);
    if (!event) {
      console.warn('[CalendarApp] Event not found:', eventId);
      return;
    }

    try {
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

      console.log('[CalendarApp] Moving event:', eventId);
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
    } catch (error) {
      console.error('[CalendarApp] Error moving event:', error);
      setError('Failed to move event');
    }
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

  // Display error if WebSocket is not available
  if (error) {
    return (
      <div className="calendar-app">
        <div style={{
          padding: '2rem',
          textAlign: 'center',
          color: '#d32f2f'
        }}>
          <h3>⚠️ Calendar Error</h3>
          <p>{error}</p>
          <button
            className="btn-primary"
            onClick={() => setError(null)}
            style={{ marginTop: '1rem' }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

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
