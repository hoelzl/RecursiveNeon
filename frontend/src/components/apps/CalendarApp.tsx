import { useState, useEffect, useCallback } from 'react';
import type { CalendarEvent, CalendarView, CreateEventData } from '../../types';
import { useWebSocket } from '../../contexts/WebSocketContext';
import { timeService } from '../../services/timeService';
import { CalendarHeader } from './calendar/CalendarHeader';
import { MonthView } from './calendar/MonthView';
import { WeekView } from './calendar/WeekView';
import { DayView } from './calendar/DayView';
import { ListView } from './calendar/ListView';
import { EventModal } from './calendar/EventModal';
import '../../styles/calendar.css';

export function CalendarApp() {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [selectedDate, setSelectedDate] = useState<Date>(timeService.getCurrentTime());
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

    // Handler for calendar events list
    const handleEventsList = (msg: any) => {
      try {
        if (msg.data && Array.isArray(msg.data.events)) {
          console.log('[CalendarApp] Loaded events:', msg.data.events.length);
          setEvents(msg.data.events);
        }
      } catch (error) {
        console.error('[CalendarApp] Error handling events list:', error);
        setError('Error loading events');
      }
    };

    // Handler for calendar event created
    const handleEventCreated = (msg: any) => {
      try {
        if (msg.data && msg.data.event) {
          console.log('[CalendarApp] Event created:', msg.data.event.id);
          setEvents(prev => [...prev, msg.data.event]);
        }
      } catch (error) {
        console.error('[CalendarApp] Error handling event created:', error);
      }
    };

    // Handler for calendar event updated
    const handleEventUpdated = (msg: any) => {
      try {
        if (msg.data && msg.data.event) {
          console.log('[CalendarApp] Event updated:', msg.data.event.id);
          setEvents(prev => prev.map(e =>
            e.id === msg.data.event.id ? msg.data.event : e
          ));
        }
      } catch (error) {
        console.error('[CalendarApp] Error handling event updated:', error);
      }
    };

    // Handler for calendar event deleted
    const handleEventDeleted = (msg: any) => {
      try {
        if (msg.data && msg.data.event_id) {
          console.log('[CalendarApp] Event deleted:', msg.data.event_id);
          setEvents(prev => prev.filter(e => e.id !== msg.data.event_id));
        }
      } catch (error) {
        console.error('[CalendarApp] Error handling event deleted:', error);
      }
    };

    try {
      console.log('[CalendarApp] Registering message handlers');

      // Register handlers using the WebSocketClient API
      wsClient.on('calendar_events_list', handleEventsList);
      wsClient.on('calendar_event_created', handleEventCreated);
      wsClient.on('calendar_event_updated', handleEventUpdated);
      wsClient.on('calendar_event_deleted', handleEventDeleted);

      return () => {
        console.log('[CalendarApp] Unregistering message handlers');
        try {
          wsClient.off('calendar_events_list', handleEventsList);
          wsClient.off('calendar_event_created', handleEventCreated);
          wsClient.off('calendar_event_updated', handleEventUpdated);
          wsClient.off('calendar_event_deleted', handleEventDeleted);
        } catch (error) {
          console.error('[CalendarApp] Error unregistering handlers:', error);
        }
      };
    } catch (error) {
      console.error('[CalendarApp] Error setting up message handlers:', error);
      setError('Failed to setup message handlers');
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
