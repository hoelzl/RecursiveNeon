/**
 * Terminal input component
 * Handles command input, history navigation, and tab completion
 */

import React, { useState, useRef, useEffect, KeyboardEvent } from 'react';

interface TerminalInputProps {
  prompt: string;
  onSubmit: (command: string) => void;
  onHistoryUp: () => string | null;
  onHistoryDown: () => string | null;
  onTabComplete: (input: string, cursorPos: number) => Promise<{ completed: string; showSuggestions: string[] }>;
  disabled?: boolean;
}

export function TerminalInput({
  prompt,
  onSubmit,
  onHistoryUp,
  onHistoryDown,
  onTabComplete,
  disabled = false,
}: TerminalInputProps) {
  const [input, setInput] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [cursorPosition, setCursorPosition] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

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
    // Clear suggestions on most keys
    if (e.key !== 'Tab') {
      setSuggestions([]);
    }

    // Enter - Submit command
    if (e.key === 'Enter') {
      e.preventDefault();
      if (input.trim()) {
        onSubmit(input);
        setInput('');
        setCursorPosition(0);
      }
      return;
    }

    // Tab - Command completion
    if (e.key === 'Tab') {
      e.preventDefault();

      const result = await onTabComplete(input, cursorPosition);

      if (result.completed !== input) {
        setInput(result.completed);
        setCursorPosition(result.completed.length);
      }

      if (result.showSuggestions.length > 1) {
        setSuggestions(result.showSuggestions);
      } else {
        setSuggestions([]);
      }

      return;
    }

    // Up arrow - History previous
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      const historyItem = onHistoryUp();
      if (historyItem !== null) {
        setInput(historyItem);
        setCursorPosition(historyItem.length);
      }
      return;
    }

    // Down arrow - History next
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
            <span key={index} className="terminal-suggestion">
              {suggestion}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
