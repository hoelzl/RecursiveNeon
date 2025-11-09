/**
 * Dialog component for in-desktop prompts and confirmations
 */
import React, { useState, useEffect } from 'react';

interface DialogProps {
  title: string;
  message?: string;
  defaultValue?: string;
  onConfirm: (value?: string) => void;
  onCancel: () => void;
  showInput?: boolean;
}

export function Dialog({ title, message, defaultValue = '', onConfirm, onCancel, showInput = true }: DialogProps) {
  const [inputValue, setInputValue] = useState(defaultValue);
  const inputRef = React.useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Focus the input when dialog opens
    inputRef.current?.focus();
    inputRef.current?.select();
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onConfirm(showInput ? inputValue : undefined);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onCancel();
    }
  };

  return (
    <div className="dialog-overlay" onClick={onCancel}>
      <div className="dialog" onClick={(e) => e.stopPropagation()} onKeyDown={handleKeyDown}>
        <div className="dialog-header">
          <h3>{title}</h3>
        </div>
        <div className="dialog-content">
          {message && <p>{message}</p>}
          {showInput && (
            <form onSubmit={handleSubmit}>
              <input
                ref={inputRef}
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                className="dialog-input"
              />
            </form>
          )}
        </div>
        <div className="dialog-actions">
          <button onClick={onCancel} className="dialog-btn dialog-btn-cancel">
            Cancel
          </button>
          <button onClick={() => onConfirm(showInput ? inputValue : undefined)} className="dialog-btn dialog-btn-confirm">
            OK
          </button>
        </div>
      </div>
    </div>
  );
}
