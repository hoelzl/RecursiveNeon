/**
 * Terminal input component
 * Handles command input, history navigation, and tab completion
 */

import React, { useState, useRef, useEffect, KeyboardEvent, forwardRef, useImperativeHandle } from 'react';

interface TerminalInputProps {
  prompt: string;
  onSubmit: (command: string) => void;
  onHistoryUp: () => string | null;
  onHistoryDown: () => string | null;
  onTabComplete: (input: string, cursorPos: number) => Promise<{
    completed: string;
    showSuggestions: string[];
    replaceStart?: number;
    replaceEnd?: number;
  }>;
  disabled?: boolean;
}

export interface TerminalInputRef {
  focus: () => void;
}

export const TerminalInput = forwardRef<TerminalInputRef, TerminalInputProps>(({
  prompt,
  onSubmit,
  onHistoryUp,
  onHistoryDown,
  onTabComplete,
  disabled = false,
}, ref) => {
  const [input, setInput] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [selectedSuggestionIndex, setSelectedSuggestionIndex] = useState<number>(-1);
  const [cursorPosition, setCursorPosition] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  // Store replace indices for suggestion cycling
  const [replaceIndices, setReplaceIndices] = useState<{ start: number; end: number } | null>(null);

  // Expose focus method to parent
  useImperativeHandle(ref, () => ({
    focus: () => {
      if (inputRef.current) {
        inputRef.current.focus();
      }
    },
  }));

  // Focus input on mount
  useEffect(() => {
    if (inputRef.current && !disabled) {
      inputRef.current.focus();
    }
  }, [disabled]);

  // Update cursor position when input changes
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.setSelectionRange(cursorPosition, cursorPosition);
    }
  }, [cursorPosition, input]);

  const handleKeyDown = async (e: KeyboardEvent<HTMLInputElement>) => {
    // Handle suggestions interactions first
    if (suggestions.length > 0) {
      // Enter - Select highlighted suggestion
      if (e.key === 'Enter' && selectedSuggestionIndex >= 0) {
        e.preventDefault();
        const selected = suggestions[selectedSuggestionIndex];
        // Use replaceIndices to properly replace the completion
        if (replaceIndices) {
          const newInput =
            input.substring(0, replaceIndices.start) +
            selected +
            input.substring(replaceIndices.end);
          setInput(newInput);
          setCursorPosition(newInput.length);
        } else {
          // Fallback to naive replacement (shouldn't happen with proper state)
          const parts = input.split(/\s+/);
          parts[parts.length - 1] = selected;
          const newInput = parts.join(' ');
          setInput(newInput);
          setCursorPosition(newInput.length);
        }
        setSuggestions([]);
        setSelectedSuggestionIndex(-1);
        setReplaceIndices(null);
        return;
      }

      // Escape - Clear suggestions
      if (e.key === 'Escape') {
        e.preventDefault();
        setSuggestions([]);
        setSelectedSuggestionIndex(-1);
        setReplaceIndices(null);
        return;
      }

      // Arrow keys - Navigate suggestions
      if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
        e.preventDefault();
        if (e.key === 'ArrowUp') {
          setSelectedSuggestionIndex((prev) =>
            prev <= 0 ? suggestions.length - 1 : prev - 1
          );
        } else {
          setSelectedSuggestionIndex((prev) =>
            prev >= suggestions.length - 1 ? 0 : prev + 1
          );
        }
        return;
      }

      // Tab - Cycle through suggestions
      if (e.key === 'Tab') {
        e.preventDefault();
        if (suggestions.length > 0 && replaceIndices) {
          // Cycle to next suggestion
          const nextIndex = (selectedSuggestionIndex + 1) % suggestions.length;
          setSelectedSuggestionIndex(nextIndex);
          // Update input with selected suggestion using stored replace indices
          const selected = suggestions[nextIndex];
          const newInput =
            input.substring(0, replaceIndices.start) +
            selected +
            input.substring(replaceIndices.end);
          setInput(newInput);
          setCursorPosition(newInput.length);
          // Update replaceEnd to reflect the new input length for the next cycle
          setReplaceIndices({ start: replaceIndices.start, end: newInput.length });
        }
        return;
      }

      // Any other key - Clear suggestions
      if (!['Shift', 'Control', 'Alt', 'Meta'].includes(e.key)) {
        setSuggestions([]);
        setSelectedSuggestionIndex(-1);
        setReplaceIndices(null);
      }
    }

    // Clear suggestions on most keys (if not already cleared above)
    if (e.key !== 'Tab' && suggestions.length === 0) {
      setSuggestions([]);
      setSelectedSuggestionIndex(-1);
      setReplaceIndices(null);
    }

    // Enter - Submit command
    if (e.key === 'Enter') {
      e.preventDefault();
      if (input.trim()) {
        onSubmit(input);
        setInput('');
        setCursorPosition(0);
        setSuggestions([]);
        setSelectedSuggestionIndex(-1);
        setReplaceIndices(null);
      }
      return;
    }

    // Tab - Command completion (when no suggestions shown)
    if (e.key === 'Tab') {
      e.preventDefault();

      const result = await onTabComplete(input, cursorPosition);

      if (result.completed !== input) {
        setInput(result.completed);
        setCursorPosition(result.completed.length);
      }

      if (result.showSuggestions.length > 1) {
        setSuggestions(result.showSuggestions);
        setSelectedSuggestionIndex(0); // Start with first suggestion selected
        // Store the replace indices for cycling through suggestions
        // IMPORTANT: These indices must reflect the COMPLETED input, not the original input
        if (result.replaceStart !== undefined && result.replaceEnd !== undefined) {
          // After completing to common prefix, the end position is now at the end of completed input
          setReplaceIndices({ start: result.replaceStart, end: result.completed.length });
        } else {
          // Fallback: assume we replace from where completion started to end of input
          setReplaceIndices({ start: result.completed.length - result.showSuggestions[0].length, end: result.completed.length });
        }
      } else {
        setSuggestions([]);
        setSelectedSuggestionIndex(-1);
        setReplaceIndices(null);
      }

      return;
    }

    // Up arrow - History previous (when no suggestions shown)
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      const historyItem = onHistoryUp();
      if (historyItem !== null) {
        setInput(historyItem);
        setCursorPosition(historyItem.length);
      }
      return;
    }

    // Down arrow - History next (when no suggestions shown)
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      const historyItem = onHistoryDown();
      if (historyItem !== null) {
        setInput(historyItem);
        setCursorPosition(historyItem.length);
      }
      return;
    }

    // Ctrl+C - Clear input
    if (e.ctrlKey && e.key === 'c') {
      e.preventDefault();
      setInput('');
      setCursorPosition(0);
      setSuggestions([]);
      setReplaceIndices(null);
      return;
    }

    // Ctrl+L - Clear screen (handled by parent)
    if (e.ctrlKey && e.key === 'l') {
      e.preventDefault();
      onSubmit('clear');
      return;
    }

    // Ctrl+U - Clear line before cursor
    if (e.ctrlKey && e.key === 'u') {
      e.preventDefault();
      setInput(input.substring(cursorPosition));
      setCursorPosition(0);
      return;
    }

    // Ctrl+K - Clear line after cursor
    if (e.ctrlKey && e.key === 'k') {
      e.preventDefault();
      setInput(input.substring(0, cursorPosition));
      return;
    }

    // Ctrl+A - Move to start
    if (e.ctrlKey && e.key === 'a') {
      e.preventDefault();
      setCursorPosition(0);
      return;
    }

    // Ctrl+E - Move to end
    if (e.ctrlKey && e.key === 'e') {
      e.preventDefault();
      setCursorPosition(input.length);
      return;
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInput(e.target.value);
    setCursorPosition(e.target.selectionStart || 0);
  };

  const handleClick = (e: React.MouseEvent<HTMLInputElement>) => {
    const target = e.target as HTMLInputElement;
    setCursorPosition(target.selectionStart || 0);
  };

  const handleSuggestionClick = (suggestion: string, index: number) => {
    // Use replaceIndices to properly replace the completion
    if (replaceIndices) {
      const newInput =
        input.substring(0, replaceIndices.start) +
        suggestion +
        input.substring(replaceIndices.end);
      setInput(newInput);
      setCursorPosition(newInput.length);
    } else {
      // Fallback to naive replacement (shouldn't happen with proper state)
      const parts = input.split(/\s+/);
      parts[parts.length - 1] = suggestion;
      const newInput = parts.join(' ');
      setInput(newInput);
      setCursorPosition(newInput.length);
    }
    setSuggestions([]);
    setSelectedSuggestionIndex(-1);
    setReplaceIndices(null);
    // Refocus input
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  return (
    <div className="terminal-input-area">
      <div className="terminal-input-line">
        <span className="terminal-prompt">{prompt}</span>
        <input
          ref={inputRef}
          type="text"
          className="terminal-input"
          value={input}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onClick={handleClick}
          disabled={disabled}
          autoComplete="off"
          spellCheck={false}
        />
      </div>

      {suggestions.length > 0 && (
        <div className="terminal-suggestions">
          {suggestions.map((suggestion, index) => (
            <span
              key={index}
              className={`terminal-suggestion ${
                index === selectedSuggestionIndex ? 'terminal-suggestion-selected' : ''
              }`}
              onClick={() => handleSuggestionClick(suggestion, index)}
              style={{ cursor: 'pointer' }}
            >
              {suggestion}
            </span>
          ))}
        </div>
      )}
    </div>
  );
});
