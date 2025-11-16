/**
 * Terminal application component
 * Main container for the terminal emulator
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { TerminalSession } from '../../terminal/core/TerminalSession';
import { CommandRegistry } from '../../terminal/core/CommandRegistry';
import { CompletionEngine } from '../../terminal/core/CompletionEngine';
import { ArgumentParser } from '../../terminal/core/ArgumentParser';
import { builtinCommands } from '../../terminal/commands/builtins';
import { Command, TerminalTheme } from '../../terminal/types';
import { TerminalOutput } from '../terminal/TerminalOutput';
import { TerminalInput, TerminalInputRef } from '../terminal/TerminalInput';
import { defaultTheme } from '../../terminal/themes/presets';
import { useWebSocket } from '../../contexts/WebSocketContext';
import { AppAPI } from '../../utils/appApi';

interface TerminalAppProps {
  initialDirectory?: string;
  theme?: TerminalTheme;
  customCommands?: Command[];
}

export function TerminalApp({
  initialDirectory = '/',
  theme = defaultTheme,
  customCommands = [],
}: TerminalAppProps) {
  const wsClient = useWebSocket();
  const api = new AppAPI(wsClient);

  const [session] = useState(() => new TerminalSession(api, initialDirectory));
  const [registry] = useState(() => {
    const reg = new CommandRegistry();
    // Register built-in commands
    reg.registerAll(builtinCommands);
    // Register custom commands
    reg.registerAll(customCommands);
    return reg;
  });
  const [argParser] = useState(() => new ArgumentParser());
  const [completionEngine] = useState(() => new CompletionEngine(registry, argParser));

  const [outputLines, setOutputLines] = useState(session.outputBuffer);
  const [currentApp, setCurrentApp] = useState(session.getCurrentApp());
  const [forceUpdate, setForceUpdate] = useState(0);
  const initRef = useRef(false);
  const inputRef = useRef<TerminalInputRef>(null);

  // Initialize session
  useEffect(() => {
    const initSession = async () => {
      // Prevent double initialization (e.g., in React StrictMode)
      if (initRef.current) {
        return;
      }
      initRef.current = true;

      try {
        await session.init();

        // Write welcome message
        session.writeLine('Welcome to RecursiveNeon Terminal v1.0', {
          color: 'var(--terminal-cyan, #00ffff)',
          bold: true,
        });
        session.writeLine("Type 'help' for available commands.");
        session.writeLine('');

        // Force update to show welcome message
        setOutputLines([...session.outputBuffer]);
      } catch (error) {
        console.error('Failed to initialize terminal:', error);
        session.writeError('Failed to initialize file system');
      }
    };

    initSession();

    // Subscribe to output changes
    const unsubscribe = session.onOutputChange(() => {
      setOutputLines([...session.outputBuffer]);
      setCurrentApp(session.getCurrentApp());
    });

    return () => {
      unsubscribe();
    };
  }, [session]);

  // Handle command execution
  const handleCommand = useCallback(
    async (command: string) => {
      // Check if we're waiting for readline input (interactive command)
      if (session.isWaitingForReadLine()) {
        // Resolve the readline promise with the input
        session.resolveReadLine(command);
        // Update output to show the input was received
        setOutputLines([...session.outputBuffer]);
        return;
      }

      if (!command.trim()) {
        session.writeLine('');
        setOutputLines([...session.outputBuffer]);
        return;
      }

      // Echo the command with prompt
      session.writeLine(`${session.getPrompt()}${command}`, {
        color: 'var(--terminal-input, inherit)',
      });

      // Add to history
      session.addToHistory(command);

      // Parse command using ArgumentParser
      const parsed = argParser.parseCommandLine(command);
      const commandName = parsed.command;
      const args = parsed.args;

      try {
        // Execute the command
        await registry.execute(commandName, {
          session,
          args,
          options: new Map(),
          rawInput: command,
          api,
          registry, // Pass registry for help/man commands
        } as any);
      } catch (error: any) {
        session.writeError(`${commandName}: ${error.message}`);
      }

      // Update output
      setOutputLines([...session.outputBuffer]);
      setCurrentApp(session.getCurrentApp());
    },
    [session, registry, api]
  );

  // Handle history navigation
  const handleHistoryUp = useCallback(() => {
    return session.navigateHistory('up');
  }, [session]);

  const handleHistoryDown = useCallback(() => {
    return session.navigateHistory('down');
  }, [session]);

  // Handle tab completion
  const handleTabComplete = useCallback(
    async (input: string, cursorPos: number) => {
      try {
        const result = await completionEngine.complete(session, input, cursorPos);

        if (result.completions.length === 0) {
          // No completions
          return { completed: input, showSuggestions: [] };
        }

        // Use replaceStart/replaceEnd if provided, otherwise use prefix-based replacement
        const replaceStart = result.replaceStart ?? (cursorPos - result.prefix.length);
        const replaceEnd = result.replaceEnd ?? cursorPos;

        if (result.completions.length === 1) {
          // Single completion - complete it
          // Don't add space if it's a directory (ends with /)
          const completion = result.completions[0];
          const shouldAddSpace = !completion.endsWith('/');
          const completed =
            input.substring(0, replaceStart) +
            completion +
            (shouldAddSpace ? ' ' : '') +
            input.substring(replaceEnd);
          return { completed, showSuggestions: [] };
        } else {
          // Multiple completions - show them and complete to common prefix
          let completed = input;

          if (result.commonPrefix.length > result.prefix.length) {
            completed =
              input.substring(0, replaceStart) +
              result.commonPrefix +
              input.substring(replaceEnd);
          }

          return { completed, showSuggestions: result.completions };
        }
      } catch (error) {
        console.error('Tab completion error:', error);
        return { completed: input, showSuggestions: [] };
      }
    },
    [session, completionEngine]
  );

  // Handle key presses (for app mode)
  useEffect(() => {
    const handleKeyPress = async (e: KeyboardEvent) => {
      if (currentApp) {
        e.preventDefault();

        const modifiers = {
          ctrl: e.ctrlKey,
          alt: e.altKey,
          shift: e.shiftKey,
          meta: e.metaKey,
        };

        const continueRunning = await session.handleKeyPress(e.key, modifiers);

        if (!continueRunning) {
          setCurrentApp(null);
        }

        setForceUpdate((prev) => prev + 1);
      }
    };

    if (currentApp) {
      window.addEventListener('keydown', handleKeyPress);
      return () => window.removeEventListener('keydown', handleKeyPress);
    }
  }, [currentApp, session]);

  // Apply theme
  const themeStyle = {
    '--terminal-bg': theme.background,
    '--terminal-fg': theme.foreground,
    '--terminal-cursor': theme.cursor,
    '--terminal-cursor-accent': theme.cursorAccent,
    '--terminal-selection': theme.selection,
    '--terminal-font': theme.fontFamily,
    '--terminal-font-size': `${theme.fontSize}px`,
    '--terminal-line-height': theme.lineHeight,
    '--terminal-opacity': theme.opacity,
    '--terminal-blur': theme.blur ? `${theme.blur}px` : '0px',
    '--terminal-cyan': theme.cyan,
    '--terminal-error': theme.red,
    '--terminal-system': theme.yellow,
  } as React.CSSProperties;

  // Determine which prompt to show
  const isWaitingForInput = session.isWaitingForReadLine();
  const currentPrompt = isWaitingForInput
    ? session.getReadLinePrompt()
    : session.getPrompt();

  // Handle clicks on terminal to focus input
  const handleTerminalClick = useCallback(() => {
    if (!currentApp && inputRef.current) {
      inputRef.current.focus();
    }
  }, [currentApp]);

  return (
    <div className="terminal-app" style={themeStyle} onClick={handleTerminalClick}>
      <TerminalOutput lines={outputLines} currentApp={currentApp} />
      {!currentApp && (
        <TerminalInput
          ref={inputRef}
          prompt={currentPrompt}
          onSubmit={handleCommand}
          onHistoryUp={handleHistoryUp}
          onHistoryDown={handleHistoryDown}
          onTabComplete={handleTabComplete}
        />
      )}
    </div>
  );
}
