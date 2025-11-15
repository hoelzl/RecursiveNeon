import type { CalendarView } from '../../../types';
import { timeService } from '../../../services/timeService';

interface CalendarHeaderProps {
  currentView: CalendarView;
  selectedDate: Date;
  onViewChange: (view: CalendarView) => void;
  onDateChange: (date: Date) => void;
  onCreateEvent: () => void;
}

export function CalendarHeader({
  currentView,
  selectedDate,
  onViewChange,
  onDateChange,
  onCreateEvent
}: CalendarHeaderProps) {
  const handlePrevious = () => {
    const newDate = new Date(selectedDate);

    switch (currentView) {
      case 'month':
        newDate.setMonth(newDate.getMonth() - 1);
        break;
      case 'week':
        newDate.setDate(newDate.getDate() - 7);
        break;
      case 'day':
        newDate.setDate(newDate.getDate() - 1);
        break;
    }

    onDateChange(newDate);
  };

  const handleNext = () => {
    const newDate = new Date(selectedDate);

    switch (currentView) {
      case 'month':
        newDate.setMonth(newDate.getMonth() + 1);
        break;
      case 'week':
        newDate.setDate(newDate.getDate() + 7);
        break;
      case 'day':
        newDate.setDate(newDate.getDate() + 1);
        break;
    }

    onDateChange(newDate);
  };

  const handleToday = () => {
    onDateChange(timeService.getCurrentTime());
  };

  const getHeaderTitle = () => {
    const monthNames = [
      'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December'
    ];

    switch (currentView) {
      case 'month':
        return `${monthNames[selectedDate.getMonth()]} ${selectedDate.getFullYear()}`;
      case 'week':
        return `Week of ${monthNames[selectedDate.getMonth()]} ${selectedDate.getDate()}, ${selectedDate.getFullYear()}`;
      case 'day':
        return `${monthNames[selectedDate.getMonth()]} ${selectedDate.getDate()}, ${selectedDate.getFullYear()}`;
      case 'list':
        return 'All Events';
      default:
        return '';
    }
  };

  return (
    <div className="calendar-header">
      <div className="calendar-header-left">
        <button className="btn-primary" onClick={onCreateEvent}>
          + New Event
        </button>
        <button className="btn-secondary" onClick={handleToday}>
          Today
        </button>
      </div>

      <div className="calendar-header-center">
        <button className="btn-nav" onClick={handlePrevious}>
          ‹
        </button>
        <h2 className="calendar-title">{getHeaderTitle()}</h2>
        <button className="btn-nav" onClick={handleNext}>
          ›
        </button>
      </div>

      <div className="calendar-header-right">
        <div className="view-switcher">
          <button
            className={`btn-view ${currentView === 'month' ? 'active' : ''}`}
            onClick={() => onViewChange('month')}
          >
            Month
          </button>
          <button
            className={`btn-view ${currentView === 'week' ? 'active' : ''}`}
            onClick={() => onViewChange('week')}
          >
            Week
          </button>
          <button
            className={`btn-view ${currentView === 'day' ? 'active' : ''}`}
            onClick={() => onViewChange('day')}
          >
            Day
          </button>
          <button
            className={`btn-view ${currentView === 'list' ? 'active' : ''}`}
            onClick={() => onViewChange('list')}
          >
            List
          </button>
        </div>
      </div>
    </div>
  );
}
