import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Desktop } from '../Desktop';
import type { ReactNode } from 'react';

// Mock all the app components
vi.mock('../apps/ChatApp', () => ({ ChatApp: () => <div>ChatApp</div> }));
vi.mock('../apps/NotesApp', () => ({ NotesApp: () => <div>NotesApp</div> }));
vi.mock('../apps/TaskListApp', () => ({ TaskListApp: () => <div>TaskListApp</div> }));
vi.mock('../apps/FileBrowserApp', () => ({ FileBrowserApp: () => <div>FileBrowserApp</div> }));
vi.mock('../apps/TextEditorApp', () => ({ TextEditorApp: () => <div>TextEditorApp</div> }));
vi.mock('../apps/ImageViewerApp', () => ({ ImageViewerApp: () => <div>ImageViewerApp</div> }));
vi.mock('../apps/WebBrowserApp', () => ({ WebBrowserApp: () => <div>WebBrowserApp</div> }));
vi.mock('../apps/TerminalApp', () => ({ TerminalApp: () => <div>TerminalApp</div> }));
vi.mock('../apps/CalendarApp', () => ({ CalendarApp: () => <div>CalendarApp</div> }));
vi.mock('../apps/NotificationDemoApp', () => ({ NotificationDemoApp: () => <div>NotificationDemoApp</div> }));
vi.mock('../apps/SettingsApp', () => ({ SettingsApp: () => <div>SettingsApp</div> }));
vi.mock('../apps/MediaViewerApp', () => ({ MediaViewerApp: () => <div>MediaViewerApp</div> }));
vi.mock('../apps/minigames/PortScannerApp', () => ({ PortScannerApp: () => <div>PortScannerApp</div> }));
vi.mock('../apps/minigames/CircuitBreakerApp', () => ({ CircuitBreakerApp: () => <div>CircuitBreakerApp</div> }));

// Mock Window component
vi.mock('../Window', () => ({
  Window: ({ window }: { window: any }) => (
    <div data-testid={`window-${window.id}`}>
      <div>{window.title}</div>
      <div>{window.content}</div>
    </div>
  ),
}));

// Mock other components
vi.mock('../Taskbar', () => ({ Taskbar: () => <div data-testid="taskbar">Taskbar</div> }));
vi.mock('../ErrorBoundary', () => ({ ErrorBoundary: ({ children }: { children: ReactNode }) => <>{children}</> }));
vi.mock('../notifications/NotificationContainer', () => ({ NotificationContainer: () => <div data-testid="notifications">Notifications</div> }));
vi.mock('../ClockWidget', () => ({ ClockWidget: () => <div data-testid="clock">Clock</div> }));
vi.mock('../apps/minigames/MinigameErrorBoundary', () => ({ MinigameErrorBoundary: ({ children }: { children: ReactNode }) => <>{children}</> }));

// Mock the game store
const mockOpenWindow = vi.fn();
const mockCloseWindow = vi.fn();
const mockMinimizeWindow = vi.fn();
const mockFocusWindow = vi.fn();
const mockUpdateWindow = vi.fn();

let mockWindows: any[] = [];
let mockNpcs: any[] = [];

vi.mock('../../stores/gameStore', () => ({
  useGameStore: () => ({
    windows: mockWindows,
    npcs: mockNpcs,
    openWindow: mockOpenWindow,
    closeWindow: mockCloseWindow,
    minimizeWindow: mockMinimizeWindow,
    focusWindow: mockFocusWindow,
    updateWindow: mockUpdateWindow,
  }),
}))

describe('Desktop', () => {
  beforeEach(() => {
    // Reset all mocks before each test
    vi.clearAllMocks();
    mockWindows = [];
    mockNpcs = [];
  });

  describe('Desktop Icons', () => {
    it('should render all desktop icons', () => {
      const { container } = render(<Desktop />);

      // Get desktop icons container
      const iconsContainer = container.querySelector('.desktop-icons');
      expect(iconsContainer).toBeInTheDocument();

      // Check for all expected icons within the icons container
      const iconLabels = Array.from(iconsContainer?.querySelectorAll('.desktop-icon-label') || [])
        .map((el) => el.textContent);

      expect(iconLabels).toContain('Chat');
      expect(iconLabels).toContain('NPCs');
      expect(iconLabels).toContain('About');
      expect(iconLabels).toContain('Notes');
      expect(iconLabels).toContain('Tasks');
      expect(iconLabels).toContain('Calendar');
      expect(iconLabels).toContain('Files');
      expect(iconLabels).toContain('Text Editor');
      expect(iconLabels).toContain('Images');
      expect(iconLabels).toContain('Browser');
      expect(iconLabels).toContain('Terminal');
      expect(iconLabels).toContain('PortScanner');
      expect(iconLabels).toContain('CircuitBreaker');
      expect(iconLabels).toContain('Notifications');
      expect(iconLabels).toContain('Settings');
      expect(iconLabels).toContain('MindSync');
    });

    it('should open Chat window on double-click', () => {
      const { container } = render(<Desktop />);

      const iconsContainer = container.querySelector('.desktop-icons');
      const chatIcon = Array.from(iconsContainer?.querySelectorAll('.desktop-icon') || [])
        .find((icon) => icon.textContent?.includes('Chat'));

      fireEvent.doubleClick(chatIcon!);

      expect(mockOpenWindow).toHaveBeenCalledWith({
        title: 'Chat',
        type: 'chat',
        content: expect.anything(),
        position: { x: 100, y: 100 },
        size: { width: 800, height: 600 },
        minimized: false,
      });
    });

    it('should open Notes window on double-click', () => {
      const { container } = render(<Desktop />);

      const iconsContainer = container.querySelector('.desktop-icons');
      const notesIcon = Array.from(iconsContainer?.querySelectorAll('.desktop-icon') || [])
        .find((icon) => icon.textContent?.includes('Notes'));

      fireEvent.doubleClick(notesIcon!);

      expect(mockOpenWindow).toHaveBeenCalledWith({
        title: 'Notes',
        type: 'notes',
        content: expect.anything(),
        position: { x: 120, y: 120 },
        size: { width: 900, height: 600 },
        minimized: false,
      });
    });

    it('should open Files window on double-click', () => {
      const { container } = render(<Desktop />);

      const iconsContainer = container.querySelector('.desktop-icons');
      const filesIcon = Array.from(iconsContainer?.querySelectorAll('.desktop-icon') || [])
        .find((icon) => icon.textContent?.includes('Files'));

      fireEvent.doubleClick(filesIcon!);

      expect(mockOpenWindow).toHaveBeenCalledWith({
        title: 'File Browser',
        type: 'files',
        content: expect.anything(),
        position: { x: 160, y: 160 },
        size: { width: 800, height: 600 },
        minimized: false,
      });
    });

    it('should open Terminal window on double-click', () => {
      const { container } = render(<Desktop />);

      const iconsContainer = container.querySelector('.desktop-icons');
      const terminalIcon = Array.from(iconsContainer?.querySelectorAll('.desktop-icon') || [])
        .find((icon) => icon.textContent?.includes('Terminal'));

      fireEvent.doubleClick(terminalIcon!);

      expect(mockOpenWindow).toHaveBeenCalledWith({
        title: 'Terminal',
        type: 'terminal',
        content: expect.anything(),
        position: { x: 240, y: 240 },
        size: { width: 900, height: 650 },
        minimized: false,
      });
    });

    it('should open NPC Directory with available NPCs', () => {
      mockNpcs = [
        {
          id: 'npc1',
          name: 'Alice',
          avatar: '👩',
          occupation: 'Engineer',
          location: 'Lab',
          background: 'A skilled engineer',
        },
        {
          id: 'npc2',
          name: 'Bob',
          avatar: '👨',
          occupation: 'Doctor',
          location: 'Hospital',
          background: 'A caring doctor',
        },
      ];
      const { container } = render(<Desktop />);

      const iconsContainer = container.querySelector('.desktop-icons');
      const npcsIcon = Array.from(iconsContainer?.querySelectorAll('.desktop-icon') || [])
        .find((icon) => icon.textContent?.includes('NPCs'));

      fireEvent.doubleClick(npcsIcon!);

      expect(mockOpenWindow).toHaveBeenCalledWith({
        title: 'NPC Directory',
        type: 'npc-list',
        content: expect.anything(),
        position: { x: 150, y: 150 },
        size: { width: 600, height: 500 },
        minimized: false,
      });
    });

    it('should open About window with project info', () => {
      const { container } = render(<Desktop />);

      const iconsContainer = container.querySelector('.desktop-icons');
      const aboutIcon = Array.from(iconsContainer?.querySelectorAll('.desktop-icon') || [])
        .find((icon) => icon.textContent?.includes('About'));

      fireEvent.doubleClick(aboutIcon!);

      expect(mockOpenWindow).toHaveBeenCalledWith({
        title: 'About Recursive://Neon',
        type: 'about',
        content: expect.anything(),
        position: { x: 200, y: 200 },
        size: { width: 600, height: 400 },
        minimized: false,
      });
    });
  });

  describe('Window Rendering', () => {
    it('should render no windows when windows array is empty', () => {
      render(<Desktop />);

      const windows = screen.queryAllByTestId(/^window-/);
      expect(windows).toHaveLength(0);
    });

    it('should render all open windows', () => {
      mockWindows = [
        {
          id: 'window1',
          title: 'Chat',
          type: 'chat',
          content: <div>ChatApp</div>,
          position: { x: 100, y: 100 },
          size: { width: 800, height: 600 },
          zIndex: 100,
          minimized: false,
        },
        {
          id: 'window2',
          title: 'Notes',
          type: 'notes',
          content: <div>NotesApp</div>,
          position: { x: 120, y: 120 },
          size: { width: 900, height: 600 },
          zIndex: 101,
          minimized: false,
        },
      ];
      render(<Desktop />);

      expect(screen.getByTestId('window-window1')).toBeInTheDocument();
      expect(screen.getByTestId('window-window2')).toBeInTheDocument();
    });

    it('should render window titles', () => {
      mockWindows = [
        {
          id: 'window1',
          title: 'Test Window Title',
          type: 'test',
          content: <div>Test Content</div>,
          position: { x: 100, y: 100 },
          size: { width: 800, height: 600 },
          zIndex: 100,
          minimized: false,
        },
      ];
      render(<Desktop />);

      expect(screen.getByText('Test Window Title')).toBeInTheDocument();
    });
  });

  describe('UI Components', () => {
    it('should render taskbar', () => {
      render(<Desktop />);

      expect(screen.getByTestId('taskbar')).toBeInTheDocument();
    });

    it('should render notification container', () => {
      render(<Desktop />);

      expect(screen.getByTestId('notifications')).toBeInTheDocument();
    });

    it('should render clock widget', () => {
      render(<Desktop />);

      expect(screen.getByTestId('clock')).toBeInTheDocument();
    });
  });

  describe('Desktop Layout', () => {
    it('should have desktop class', () => {
      const { container } = render(<Desktop />);

      expect(container.querySelector('.desktop')).toBeInTheDocument();
    });

    it('should have desktop icons container', () => {
      const { container } = render(<Desktop />);

      expect(container.querySelector('.desktop-icons')).toBeInTheDocument();
    });
  });
});
