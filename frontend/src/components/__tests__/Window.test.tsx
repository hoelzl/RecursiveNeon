import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Window } from '../Window';
import type { WindowState } from '../../types';

// Mock the game store
const mockCloseWindow = vi.fn();
const mockMinimizeWindow = vi.fn();
const mockFocusWindow = vi.fn();
const mockUpdateWindow = vi.fn();

vi.mock('../../stores/gameStore', () => ({
  useGameStore: () => ({
    closeWindow: mockCloseWindow,
    minimizeWindow: mockMinimizeWindow,
    focusWindow: mockFocusWindow,
    updateWindow: mockUpdateWindow,
  }),
}));

// Mock react-rnd
vi.mock('react-rnd', () => ({
  Rnd: ({ children, onDragStop, onResizeStop, ...props }: any) => {
    const handleDrag = () => {
      if (onDragStop) {
        onDragStop(null, { x: 150, y: 150 });
      }
    };

    const handleResize = () => {
      if (onResizeStop) {
        const mockElement = {
          offsetWidth: 900,
          offsetHeight: 700,
        };
        onResizeStop(null, null, mockElement, null, { x: 160, y: 160 });
      }
    };

    return (
      <div data-testid="rnd-container" {...props}>
        <button data-testid="drag-trigger" onClick={handleDrag}>
          Drag
        </button>
        <button data-testid="resize-trigger" onClick={handleResize}>
          Resize
        </button>
        {children}
      </div>
    );
  },
}));

describe('Window', () => {
  let mockWindow: WindowState;

  beforeEach(() => {
    // Reset all mocks before each test
    vi.clearAllMocks();

    mockWindow = {
      id: 'test-window',
      title: 'Test Window',
      type: 'test',
      content: <div>Test Content</div>,
      position: { x: 100, y: 100 },
      size: { width: 800, height: 600 },
      zIndex: 100,
      minimized: false,
    };
  });

  describe('Window Rendering', () => {
    it('should render window with title', () => {
      render(<Window window={mockWindow} />);

      expect(screen.getByText('Test Window')).toBeInTheDocument();
    });

    it('should render window content', () => {
      render(<Window window={mockWindow} />);

      expect(screen.getByText('Test Content')).toBeInTheDocument();
    });

    it('should render minimize button', () => {
      render(<Window window={mockWindow} />);

      const minimizeBtn = screen.getByTitle('Minimize');
      expect(minimizeBtn).toBeInTheDocument();
      expect(minimizeBtn).toHaveTextContent('−');
    });

    it('should render close button', () => {
      render(<Window window={mockWindow} />);

      const closeBtn = screen.getByTitle('Close');
      expect(closeBtn).toBeInTheDocument();
      expect(closeBtn).toHaveTextContent('×');
    });

    it('should not render when window is minimized', () => {
      mockWindow.minimized = true;
      render(<Window window={mockWindow} />);

      expect(screen.queryByText('Test Window')).not.toBeInTheDocument();
    });
  });

  describe('Window Controls', () => {
    it('should call closeWindow when close button is clicked', () => {
      render(<Window window={mockWindow} />);

      const closeBtn = screen.getByTitle('Close');
      fireEvent.click(closeBtn);

      expect(mockCloseWindow).toHaveBeenCalledWith('test-window');
    });

    it('should call minimizeWindow when minimize button is clicked', () => {
      render(<Window window={mockWindow} />);

      const minimizeBtn = screen.getByTitle('Minimize');
      fireEvent.click(minimizeBtn);

      expect(mockMinimizeWindow).toHaveBeenCalledWith('test-window');
    });

    it('should call focusWindow when window is clicked', () => {
      render(<Window window={mockWindow} />);

      const windowElement = screen.getByText('Test Content').closest('.window');
      fireEvent.mouseDown(windowElement!);

      expect(mockFocusWindow).toHaveBeenCalledWith('test-window');
    });

    it('should call focusWindow when titlebar is clicked', () => {
      render(<Window window={mockWindow} />);

      const titlebar = screen.getByText('Test Window').closest('.window-titlebar');
      fireEvent.mouseDown(titlebar!);

      expect(mockFocusWindow).toHaveBeenCalledWith('test-window');
    });
  });

  describe('Window Drag and Resize', () => {
    it('should update window position on drag stop', () => {
      render(<Window window={mockWindow} />);

      const dragTrigger = screen.getByTestId('drag-trigger');
      fireEvent.click(dragTrigger);

      expect(mockUpdateWindow).toHaveBeenCalledWith('test-window', {
        position: { x: 150, y: 150 },
      });
    });

    it('should update window size and position on resize stop', () => {
      render(<Window window={mockWindow} />);

      const resizeTrigger = screen.getByTestId('resize-trigger');
      fireEvent.click(resizeTrigger);

      expect(mockUpdateWindow).toHaveBeenCalledWith('test-window', {
        size: { width: 900, height: 700 },
        position: { x: 160, y: 160 },
      });
    });
  });

  describe('Window Styles', () => {
    it('should apply correct zIndex from window state', () => {
      mockWindow.zIndex = 150;
      const { container } = render(<Window window={mockWindow} />);

      const rndContainer = container.querySelector('[data-testid="rnd-container"]');
      expect(rndContainer).toHaveStyle({ zIndex: '150' });
    });

    it('should have full width and height styles', () => {
      render(<Window window={mockWindow} />);

      const windowElement = screen.getByText('Test Content').closest('.window');
      expect(windowElement).toHaveStyle({ width: '100%', height: '100%' });
    });
  });

  describe('Window Structure', () => {
    it('should have window-titlebar class', () => {
      const { container } = render(<Window window={mockWindow} />);

      expect(container.querySelector('.window-titlebar')).toBeInTheDocument();
    });

    it('should have window-title class', () => {
      const { container } = render(<Window window={mockWindow} />);

      expect(container.querySelector('.window-title')).toBeInTheDocument();
    });

    it('should have window-controls class', () => {
      const { container } = render(<Window window={mockWindow} />);

      expect(container.querySelector('.window-controls')).toBeInTheDocument();
    });

    it('should have window-content class', () => {
      const { container } = render(<Window window={mockWindow} />);

      expect(container.querySelector('.window-content')).toBeInTheDocument();
    });

    it('should have close button with close class', () => {
      render(<Window window={mockWindow} />);

      const closeBtn = screen.getByTitle('Close');
      expect(closeBtn).toHaveClass('window-control-btn', 'close');
    });
  });
});
