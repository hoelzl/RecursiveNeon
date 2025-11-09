/**
 * Notes App - Note-taking with title list and content editor
 */
import React, { useState, useEffect } from 'react';
import { useWebSocket } from '../../contexts/WebSocketContext';
import { AppAPI } from '../../utils/appApi';
import { Note } from '../../types';

export function NotesApp() {
  const wsClient = useWebSocket();
  const api = new AppAPI(wsClient);

  const [notes, setNotes] = useState<Note[]>([]);
  const [selectedNote, setSelectedNote] = useState<Note | null>(null);
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; noteId: string } | null>(null);
  const contentInputRef = React.useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    loadNotes();
  }, []);

  useEffect(() => {
    const handleClickOutside = () => setContextMenu(null);
    if (contextMenu) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [contextMenu]);

  const loadNotes = async () => {
    try {
      const notesList = await api.getNotes();
      setNotes(notesList);
      if (notesList.length > 0) {
        selectNote(notesList[0]);
      }
    } catch (error) {
      console.error('Failed to load notes:', error);
    } finally {
      setLoading(false);
    }
  };

  const selectNote = async (note: Note) => {
    // Auto-save current note before switching
    if (selectedNote && (title !== selectedNote.title || content !== selectedNote.content)) {
      try {
        const updated = await api.updateNote(selectedNote.id, { title, content });
        setNotes(notes.map((n) => (n.id === updated.id ? updated : n)));
      } catch (error) {
        console.error('Failed to auto-save note:', error);
      }
    }

    setSelectedNote(note);
    setTitle(note.title);
    setContent(note.content);
  };

  const handleSave = async () => {
    if (!selectedNote) return;
    try {
      const updated = await api.updateNote(selectedNote.id, { title, content });
      setNotes(notes.map((n) => (n.id === updated.id ? updated : n)));
      setSelectedNote(updated);
    } catch (error) {
      console.error('Failed to save note:', error);
    }
  };

  const handleNew = async () => {
    try {
      const newNote = await api.createNote({ title: 'New Note', content: '' });
      setNotes([...notes, newNote]);
      selectNote(newNote);
    } catch (error) {
      console.error('Failed to create note:', error);
    }
  };

  const handleDelete = async (noteId?: string) => {
    const idToDelete = noteId ?? selectedNote?.id;
    if (!idToDelete) return;

    try {
      await api.deleteNote(idToDelete);
      const remaining = notes.filter((n) => n.id !== idToDelete);
      setNotes(remaining);

      // If we deleted the selected note, select another one
      if (selectedNote?.id === idToDelete) {
        if (remaining.length > 0) {
          selectNote(remaining[0]);
        } else {
          setSelectedNote(null);
          setTitle('');
          setContent('');
        }
      }

      setContextMenu(null);
    } catch (error) {
      console.error('Failed to delete note:', error);
    }
  };

  const handleTitleKeyDown = async (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      await handleSave();
      contentInputRef.current?.focus();
    }
  };

  const handleContextMenu = (e: React.MouseEvent, noteId: string) => {
    e.preventDefault();
    setContextMenu({ x: e.clientX, y: e.clientY, noteId });
  };

  if (loading) return <div className="notes-loading">Loading notes...</div>;

  return (
    <div className="notes-app">
      <div className="notes-sidebar">
        <div className="notes-header">
          <h3>Notes</h3>
          <button onClick={handleNew}>+</button>
        </div>
        <div className="notes-list">
          {notes.map((note) => (
            <div
              key={note.id}
              className={`notes-item ${selectedNote?.id === note.id ? 'active' : ''}`}
              onClick={() => selectNote(note)}
              onContextMenu={(e) => handleContextMenu(e, note.id)}
            >
              <div className="notes-item-title">{note.title}</div>
              <div className="notes-item-date">
                {new Date(note.updated_at).toLocaleDateString()}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="notes-editor">
        {selectedNote ? (
          <>
            <div className="notes-toolbar">
              <input
                type="text"
                className="notes-title-input"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                onKeyDown={handleTitleKeyDown}
                placeholder="Note title..."
              />
              <div className="notes-actions">
                <button onClick={handleSave}>Save</button>
                <button onClick={() => handleDelete()}>Delete</button>
              </div>
            </div>
            <textarea
              ref={contentInputRef}
              className="notes-content-input"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Write your note here..."
            />
          </>
        ) : (
          <div className="notes-empty">
            <p>No note selected</p>
            <button onClick={handleNew}>Create New Note</button>
          </div>
        )}
      </div>

      {contextMenu && (
        <div
          className="context-menu"
          style={{ left: contextMenu.x, top: contextMenu.y }}
        >
          <div
            className="context-menu-item"
            onClick={() => handleDelete(contextMenu.noteId)}
          >
            Delete Note
          </div>
        </div>
      )}
    </div>
  );
}
