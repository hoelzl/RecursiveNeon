"""
Notes Service

Manages note-taking application data with CRUD operations.
"""
import uuid
from datetime import datetime
from typing import Dict, Any, List

from recursive_neon.models.app_models import Note, NotesState


class NotesService:
    """
    Service for managing notes.

    Provides CRUD operations for the note-taking application.
    """

    def __init__(self, notes_state: NotesState):
        """
        Initialize the notes service.

        Args:
            notes_state: The notes state to manage
        """
        self._state = notes_state

    def get_all(self) -> List[Note]:
        """Get all notes."""
        return self._state.notes

    def get(self, note_id: str) -> Note:
        """
        Get a specific note by ID.

        Args:
            note_id: ID of the note to retrieve

        Returns:
            The note

        Raises:
            ValueError: If note not found
        """
        for note in self._state.notes:
            if note.id == note_id:
                return note
        raise ValueError(f"Note not found: {note_id}")

    def create(self, data: Dict[str, Any]) -> Note:
        """
        Create a new note.

        Args:
            data: Note data (title, content)

        Returns:
            The created note
        """
        timestamp = datetime.now().isoformat()
        note = Note(
            id=str(uuid.uuid4()),
            title=data.get("title", "Untitled"),
            content=data.get("content", ""),
            created_at=timestamp,
            updated_at=timestamp,
        )
        self._state.notes.append(note)
        return note

    def update(self, note_id: str, data: Dict[str, Any]) -> Note:
        """
        Update an existing note.

        Args:
            note_id: ID of the note to update
            data: Updated note data

        Returns:
            The updated note

        Raises:
            ValueError: If note not found
        """
        note = self.get(note_id)
        timestamp = datetime.now().isoformat()

        for i, n in enumerate(self._state.notes):
            if n.id == note_id:
                updated = Note(
                    id=note.id,
                    title=data.get("title", note.title),
                    content=data.get("content", note.content),
                    created_at=note.created_at,
                    updated_at=timestamp,
                )
                self._state.notes[i] = updated
                return updated
        raise ValueError(f"Note not found: {note_id}")

    def delete(self, note_id: str) -> None:
        """
        Delete a note.

        Args:
            note_id: ID of the note to delete
        """
        self._state.notes = [
            note for note in self._state.notes if note.id != note_id
        ]
