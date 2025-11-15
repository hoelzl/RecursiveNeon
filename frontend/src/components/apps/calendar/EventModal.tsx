import { useState, useEffect } from 'react';
import type { CalendarEvent, CreateEventData, RecurrenceRule, RecurrenceFrequency } from '../../../types';

interface EventModalProps {
  event: CalendarEvent | null;
  selectedDate: Date;
  onSave: (data: CreateEventData | Partial<CalendarEvent>) => void;
  onDelete?: () => void;
  onClose: () => void;
}

const DEFAULT_COLORS = [
  '#4A90E2', // Blue
  '#7ED321', // Green
  '#F5A623', // Orange
  '#D0021B', // Red
  '#9013FE', // Purple
  '#50E3C2', // Teal
  '#BD10E0', // Magenta
  '#417505', // Dark Green
];

export function EventModal({
  event,
  selectedDate,
  onSave,
  onDelete,
  onClose
}: EventModalProps) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [startDate, setStartDate] = useState('');
  const [startTime, setStartTime] = useState('');
  const [endDate, setEndDate] = useState('');
  const [endTime, setEndTime] = useState('');
  const [location, setLocation] = useState('');
  const [color, setColor] = useState(DEFAULT_COLORS[0]);
  const [notes, setNotes] = useState('');
  const [allDay, setAllDay] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Recurrence state
  const [isRecurring, setIsRecurring] = useState(false);
  const [recurrenceFrequency, setRecurrenceFrequency] = useState<RecurrenceFrequency>('weekly');
  const [recurrenceInterval, setRecurrenceInterval] = useState(1);
  const [recurrenceEndType, setRecurrenceEndType] = useState<'never' | 'count' | 'until'>('never');
  const [recurrenceCount, setRecurrenceCount] = useState(10);
  const [recurrenceUntil, setRecurrenceUntil] = useState('');
  const [recurrenceByDay, setRecurrenceByDay] = useState<number[]>([]);

  useEffect(() => {
    if (event) {
      // Editing existing event
      setTitle(event.title);
      setDescription(event.description || '');

      const start = new Date(event.start_time);
      const end = new Date(event.end_time);

      setStartDate(start.toISOString().split('T')[0]);
      setStartTime(start.toTimeString().slice(0, 5));
      setEndDate(end.toISOString().split('T')[0]);
      setEndTime(end.toTimeString().slice(0, 5));

      setLocation(event.location || '');
      setColor(event.color || DEFAULT_COLORS[0]);
      setNotes(event.notes || '');
      setAllDay(event.all_day);

      // Load recurrence data
      if (event.recurrence_rule) {
        setIsRecurring(true);
        setRecurrenceFrequency(event.recurrence_rule.frequency);
        setRecurrenceInterval(event.recurrence_rule.interval);
        setRecurrenceByDay(event.recurrence_rule.by_day || []);

        if (event.recurrence_rule.count) {
          setRecurrenceEndType('count');
          setRecurrenceCount(event.recurrence_rule.count);
        } else if (event.recurrence_rule.until) {
          setRecurrenceEndType('until');
          setRecurrenceUntil(new Date(event.recurrence_rule.until).toISOString().split('T')[0]);
        } else {
          setRecurrenceEndType('never');
        }
      }
    } else {
      // Creating new event
      const dateStr = selectedDate.toISOString().split('T')[0];
      const now = new Date();
      const currentHour = now.getHours();
      const nextHour = currentHour + 1;

      setStartDate(dateStr);
      setStartTime(`${currentHour.toString().padStart(2, '0')}:00`);
      setEndDate(dateStr);
      setEndTime(`${nextHour.toString().padStart(2, '0')}:00`);
    }
  }, [event, selectedDate]);

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!title.trim()) {
      newErrors.title = 'Title is required';
    }

    if (!startDate) {
      newErrors.startDate = 'Start date is required';
    }

    if (!endDate) {
      newErrors.endDate = 'End date is required';
    }

    if (!allDay) {
      if (!startTime) {
        newErrors.startTime = 'Start time is required';
      }

      if (!endTime) {
        newErrors.endTime = 'End time is required';
      }

      // Check if end is after start
      if (startDate && startTime && endDate && endTime) {
        const start = new Date(`${startDate}T${startTime}`);
        const end = new Date(`${endDate}T${endTime}`);

        if (end <= start) {
          newErrors.endTime = 'End time must be after start time';
        }
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) {
      return;
    }

    const startDateTime = allDay
      ? new Date(`${startDate}T00:00:00`).toISOString()
      : new Date(`${startDate}T${startTime}`).toISOString();

    const endDateTime = allDay
      ? new Date(`${endDate}T23:59:59`).toISOString()
      : new Date(`${endDate}T${endTime}`).toISOString();

    // Build recurrence rule if event is recurring
    let recurrence_rule: RecurrenceRule | undefined = undefined;
    if (isRecurring) {
      recurrence_rule = {
        frequency: recurrenceFrequency,
        interval: recurrenceInterval,
        by_day: recurrenceFrequency === 'weekly' && recurrenceByDay.length > 0 ? recurrenceByDay : undefined,
      };

      if (recurrenceEndType === 'count') {
        recurrence_rule.count = recurrenceCount;
      } else if (recurrenceEndType === 'until') {
        recurrence_rule.until = new Date(recurrenceUntil).toISOString();
      }
    }

    const eventData: CreateEventData = {
      title: title.trim(),
      description: description.trim() || undefined,
      start_time: startDateTime,
      end_time: endDateTime,
      location: location.trim() || undefined,
      color,
      notes: notes.trim() || undefined,
      all_day: allDay,
      recurrence_rule
    };

    onSave(eventData);
  };

  const handleDelete = () => {
    if (window.confirm('Are you sure you want to delete this event?')) {
      onDelete?.();
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content event-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{event ? 'Edit Event' : 'New Event'}</h2>
          <button className="btn-close" onClick={onClose}>×</button>
        </div>

        <form onSubmit={handleSubmit} className="event-form">
          <div className="form-group">
            <label htmlFor="title">Title *</label>
            <input
              id="title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Event title"
              maxLength={200}
            />
            {errors.title && <span className="error">{errors.title}</span>}
          </div>

          <div className="form-group">
            <label htmlFor="description">Description</label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Event description"
              maxLength={2000}
              rows={3}
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="startDate">Start Date *</label>
              <input
                id="startDate"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
              {errors.startDate && <span className="error">{errors.startDate}</span>}
            </div>

            {!allDay && (
              <div className="form-group">
                <label htmlFor="startTime">Start Time *</label>
                <input
                  id="startTime"
                  type="time"
                  value={startTime}
                  onChange={(e) => setStartTime(e.target.value)}
                />
                {errors.startTime && <span className="error">{errors.startTime}</span>}
              </div>
            )}
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="endDate">End Date *</label>
              <input
                id="endDate"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
              {errors.endDate && <span className="error">{errors.endDate}</span>}
            </div>

            {!allDay && (
              <div className="form-group">
                <label htmlFor="endTime">End Time *</label>
                <input
                  id="endTime"
                  type="time"
                  value={endTime}
                  onChange={(e) => setEndTime(e.target.value)}
                />
                {errors.endTime && <span className="error">{errors.endTime}</span>}
              </div>
            )}
          </div>

          <div className="form-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={allDay}
                onChange={(e) => setAllDay(e.target.checked)}
              />
              All day event
            </label>
          </div>

          <div className="form-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={isRecurring}
                onChange={(e) => setIsRecurring(e.target.checked)}
              />
              Recurring event
            </label>
          </div>

          {isRecurring && (
            <div className="recurrence-section">
              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="recurrence-frequency">Frequency</label>
                  <select
                    id="recurrence-frequency"
                    value={recurrenceFrequency}
                    onChange={(e) => setRecurrenceFrequency(e.target.value as RecurrenceFrequency)}
                    style={{
                      width: '100%',
                      padding: '0.5rem',
                      backgroundColor: '#0f3460',
                      border: '1px solid #16213e',
                      borderRadius: '4px',
                      color: '#e0e0e0',
                      fontFamily: "'Courier New', monospace"
                    }}
                  >
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                    <option value="yearly">Yearly</option>
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="recurrence-interval">Every</label>
                  <input
                    id="recurrence-interval"
                    type="number"
                    min="1"
                    max="365"
                    value={recurrenceInterval}
                    onChange={(e) => setRecurrenceInterval(parseInt(e.target.value) || 1)}
                  />
                </div>
              </div>

              {recurrenceFrequency === 'weekly' && (
                <div className="form-group">
                  <label>Repeat on</label>
                  <div className="weekday-picker" style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                    {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day, index) => (
                      <button
                        key={day}
                        type="button"
                        className={`btn-secondary ${recurrenceByDay.includes(index) ? 'active' : ''}`}
                        onClick={() => {
                          if (recurrenceByDay.includes(index)) {
                            setRecurrenceByDay(recurrenceByDay.filter(d => d !== index));
                          } else {
                            setRecurrenceByDay([...recurrenceByDay, index].sort());
                          }
                        }}
                        style={{
                          padding: '0.5rem',
                          minWidth: '50px',
                          backgroundColor: recurrenceByDay.includes(index) ? '#00d9ff' : '#0f3460',
                          color: recurrenceByDay.includes(index) ? '#1a1a2e' : '#00d9ff'
                        }}
                      >
                        {day}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div className="form-group">
                <label>Ends</label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <label className="checkbox-label">
                    <input
                      type="radio"
                      name="recurrence-end"
                      checked={recurrenceEndType === 'never'}
                      onChange={() => setRecurrenceEndType('never')}
                    />
                    Never
                  </label>

                  <label className="checkbox-label">
                    <input
                      type="radio"
                      name="recurrence-end"
                      checked={recurrenceEndType === 'count'}
                      onChange={() => setRecurrenceEndType('count')}
                    />
                    After
                    <input
                      type="number"
                      min="1"
                      max="999"
                      value={recurrenceCount}
                      onChange={(e) => setRecurrenceCount(parseInt(e.target.value) || 1)}
                      disabled={recurrenceEndType !== 'count'}
                      style={{
                        width: '80px',
                        marginLeft: '0.5rem',
                        padding: '0.25rem',
                        backgroundColor: '#0f3460',
                        border: '1px solid #16213e',
                        borderRadius: '4px',
                        color: '#e0e0e0'
                      }}
                    />
                    occurrences
                  </label>

                  <label className="checkbox-label">
                    <input
                      type="radio"
                      name="recurrence-end"
                      checked={recurrenceEndType === 'until'}
                      onChange={() => setRecurrenceEndType('until')}
                    />
                    On
                    <input
                      type="date"
                      value={recurrenceUntil}
                      onChange={(e) => setRecurrenceUntil(e.target.value)}
                      disabled={recurrenceEndType !== 'until'}
                      style={{
                        marginLeft: '0.5rem',
                        padding: '0.25rem',
                        backgroundColor: '#0f3460',
                        border: '1px solid #16213e',
                        borderRadius: '4px',
                        color: '#e0e0e0'
                      }}
                    />
                  </label>
                </div>
              </div>
            </div>
          )}

          <div className="form-group">
            <label htmlFor="location">Location</label>
            <input
              id="location"
              type="text"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="Event location"
              maxLength={200}
            />
          </div>

          <div className="form-group">
            <label>Color</label>
            <div className="color-picker">
              {DEFAULT_COLORS.map(c => (
                <button
                  key={c}
                  type="button"
                  className={`color-option ${color === c ? 'selected' : ''}`}
                  style={{ backgroundColor: c }}
                  onClick={() => setColor(c)}
                  aria-label={`Color ${c}`}
                />
              ))}
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="notes">Notes</label>
            <textarea
              id="notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Additional notes"
              maxLength={5000}
              rows={4}
            />
          </div>

          <div className="modal-footer">
            <div className="footer-left">
              {onDelete && (
                <button
                  type="button"
                  className="btn-danger"
                  onClick={handleDelete}
                >
                  Delete
                </button>
              )}
            </div>
            <div className="footer-right">
              <button type="button" className="btn-secondary" onClick={onClose}>
                Cancel
              </button>
              <button type="submit" className="btn-primary">
                Save
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
