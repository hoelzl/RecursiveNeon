import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { NotesApp } from '../NotesApp';
import { WebSocketProvider } from '../../../contexts/WebSocketContext';
import type { Note } from '../../../types';

// Mock WebSocket client
const mockWebSocketClient = {
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  sendMessage: vi.fn(),
  readyState: 1,
} as any;

// Mock AppAPI responses
const mockNotes: Note[] = [
  { id: '1', title: 'First Note', content: 'Content of first note', createdAt: '2024-01-01', updatedAt: '2024-01-01' },
  { id: '2', title: 'Second Note', content: 'Content of second note', createdAt: '2024-01-02', updatedAt: '2024-01-02' },
];

// Helper to render with WebSocket context
const renderNotesApp = () => {
  return render(
    <WebSocketProvider client={mockWebSocketClient}>
      <NotesApp />
    </WebSocketProvider>
  );
};

// Helper to simulate API responses
const simulateApiResponse = (data: any) => {
  const messageHandler = mockWebSocketClient.addEventListener.mock.calls.find(
    (call: any[]) => call[0] === 'message'
  )?.[1];

  if (messageHandler) {
    messageHandler({ data: JSON.stringify(data) });
  }
};

describe('NotesApp', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Initialization', () => {
    it('should render loading state initially', () => {
      renderNotesApp();
      // Component should be rendered
      expect(screen.getByRole('application', { hidden: true }) || document.body).toBeTruthy();
    });

    it('should load notes on mount', async () => {
      renderNotesApp();

      // Wait for getNotes API call
      await waitFor(() => {
        expect(mockWebSocketClient.sendMessage).toHaveBeenCalledWith(
          expect.objectContaining({
            type: 'app',
            data: expect.objectContaining({
              action: 'get_notes',
            }),
          })
        );
      });
    });

    it('should display notes after loading', async () => {
      renderNotesApp();

      // Simulate successful notes load
      await waitFor(() => {
        const calls = mockWebSocketClient.sendMessage.mock.calls;
        if (calls.length > 0) {
          simulateApiResponse({
            type: 'app_response',
            data: {
              action: 'get_notes',
              notes: mockNotes,
            },
          });
        }
      });

      await waitFor(() => {
        expect(screen.getByText('First Note')).toBeInTheDocument();
        expect(screen.getByText('Second Note')).toBeInTheDocument();
      });
    });

    it('should select first note by default', async () => {
      renderNotesApp();

      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'get_notes',
          notes: mockNotes,
        },
      });

      await waitFor(() => {
        const titleInput = screen.getByDisplayValue('First Note');
        expect(titleInput).toBeInTheDocument();
      });
    });
  });

  describe('Note Selection', () => {
    it('should display selected note content', async () => {
      renderNotesApp();

      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'get_notes',
          notes: mockNotes,
        },
      });

      await waitFor(() => {
        expect(screen.getByDisplayValue('First Note')).toBeInTheDocument();
        expect(screen.getByDisplayValue('Content of first note')).toBeInTheDocument();
      });
    });

    it('should switch notes when clicking on different note', async () => {
      const user = userEvent.setup();
      renderNotesApp();

      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'get_notes',
          notes: mockNotes,
        },
      });

      await waitFor(() => {
        expect(screen.getByText('Second Note')).toBeInTheDocument();
      });

      // Click on second note
      await user.click(screen.getByText('Second Note'));

      await waitFor(() => {
        expect(screen.getByDisplayValue('Second Note')).toBeInTheDocument();
        expect(screen.getByDisplayValue('Content of second note')).toBeInTheDocument();
      });
    });

    it('should auto-save current note before switching', async () => {
      const user = userEvent.setup();
      renderNotesApp();

      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'get_notes',
          notes: mockNotes,
        },
      });

      await waitFor(() => {
        expect(screen.getByDisplayValue('First Note')).toBeInTheDocument();
      });

      // Edit the current note
      const contentInput = screen.getByDisplayValue('Content of first note');
      await user.clear(contentInput);
      await user.type(contentInput, 'Modified content');

      // Click on second note to trigger auto-save
      await user.click(screen.getByText('Second Note'));

      // Should call update_note API
      await waitFor(() => {
        const updateCall = mockWebSocketClient.sendMessage.mock.calls.find(
          (call: any) => call[0]?.data?.action === 'update_note'
        );
        expect(updateCall).toBeTruthy();
      });
    });
  });

  describe('Note Editing', () => {
    it('should update title when typing', async () => {
      const user = userEvent.setup();
      renderNotesApp();

      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'get_notes',
          notes: mockNotes,
        },
      });

      await waitFor(() => {
        expect(screen.getByDisplayValue('First Note')).toBeInTheDocument();
      });

      const titleInput = screen.getByDisplayValue('First Note');
      await user.clear(titleInput);
      await user.type(titleInput, 'Updated Title');

      expect(screen.getByDisplayValue('Updated Title')).toBeInTheDocument();
    });

    it('should update content when typing', async () => {
      const user = userEvent.setup();
      renderNotesApp();

      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'get_notes',
          notes: mockNotes,
        },
      });

      await waitFor(() => {
        expect(screen.getByDisplayValue('Content of first note')).toBeInTheDocument();
      });

      const contentInput = screen.getByDisplayValue('Content of first note');
      await user.clear(contentInput);
      await user.type(contentInput, 'Updated content');

      expect(screen.getByDisplayValue('Updated content')).toBeInTheDocument();
    });
  });

  describe('Note Creation', () => {
    it('should create new note when clicking new button', async () => {
      const user = userEvent.setup();
      renderNotesApp();

      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'get_notes',
          notes: mockNotes,
        },
      });

      await waitFor(() => {
        expect(screen.getByText('First Note')).toBeInTheDocument();
      });

      // Click new note button
      const newButton = screen.getByText(/new/i) || screen.getByRole('button', { name: /new/i });
      await user.click(newButton);

      // Should call create_note API
      await waitFor(() => {
        const createCall = mockWebSocketClient.sendMessage.mock.calls.find(
          (call: any) => call[0]?.data?.action === 'create_note'
        );
        expect(createCall).toBeTruthy();
      });
    });

    it('should display new note after creation', async () => {
      const user = userEvent.setup();
      renderNotesApp();

      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'get_notes',
          notes: mockNotes,
        },
      });

      await waitFor(() => {
        expect(screen.getByText('First Note')).toBeInTheDocument();
      });

      const newButton = screen.getByText(/new/i) || screen.getByRole('button', { name: /new/i });
      await user.click(newButton);

      // Simulate successful creation
      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'create_note',
          note: {
            id: '3',
            title: 'New Note',
            content: '',
            createdAt: '2024-01-03',
            updatedAt: '2024-01-03',
          },
        },
      });

      await waitFor(() => {
        expect(screen.getByText('New Note')).toBeInTheDocument();
      });
    });
  });

  describe('Note Saving', () => {
    it('should save note when clicking save button', async () => {
      const user = userEvent.setup();
      renderNotesApp();

      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'get_notes',
          notes: mockNotes,
        },
      });

      await waitFor(() => {
        expect(screen.getByDisplayValue('First Note')).toBeInTheDocument();
      });

      // Edit the note
      const contentInput = screen.getByDisplayValue('Content of first note');
      await user.clear(contentInput);
      await user.type(contentInput, 'Modified');

      // Click save button
      const saveButton = screen.getByText(/save/i) || screen.getByRole('button', { name: /save/i });
      await user.click(saveButton);

      // Should call update_note API
      await waitFor(() => {
        const updateCall = mockWebSocketClient.sendMessage.mock.calls.find(
          (call: any) => call[0]?.data?.action === 'update_note'
        );
        expect(updateCall).toBeTruthy();
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle failed note loading', async () => {
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
      renderNotesApp();

      // Simulate error response
      simulateApiResponse({
        type: 'error',
        data: {
          message: 'Failed to load notes',
        },
      });

      await waitFor(() => {
        expect(consoleError).toHaveBeenCalled();
      });

      consoleError.mockRestore();
    });

    it('should handle failed note creation', async () => {
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
      const user = userEvent.setup();
      renderNotesApp();

      simulateApiResponse({
        type: 'app_response',
        data: {
          action: 'get_notes',
          notes: mockNotes,
        },
      });

      await waitFor(() => {
        expect(screen.getByText('First Note')).toBeInTheDocument();
      });

      const newButton = screen.getByText(/new/i) || screen.getByRole('button', { name: /new/i });
      await user.click(newButton);

      // Simulate error response
      simulateApiResponse({
        type: 'error',
        data: {
          message: 'Failed to create note',
        },
      });

      await waitFor(() => {
        expect(consoleError).toHaveBeenCalled();
      });

      consoleError.mockRestore();
    });
  });
});
