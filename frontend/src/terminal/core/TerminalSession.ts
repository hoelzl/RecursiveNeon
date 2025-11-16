/**
 * Terminal session management
 * Handles state, output, history, and command execution
 */

import { AppAPI } from '../../utils/appApi';
import { OutputLine, TextStyle, TerminalApplication } from '../types';
import { FileSystemAdapter } from './FileSystemAdapter';
import { AnsiParser } from './AnsiParser';

export class TerminalSession {
  public id: string;
  public outputBuffer: OutputLine[] = [];
  public commandHistory: string[] = [];
  public historyIndex: number = -1;
  public currentPath: string = '/';
  public environment: Map<string, string> = new Map();

  private api: AppAPI;
  private fs: FileSystemAdapter;
  private ansiParser: AnsiParser;
  private maxOutputLines: number = 1000;
  private maxHistorySize: number = 500;
  private promptTemplate: string = 'user@neon:~$';
  private currentApp: TerminalApplication | null = null;
  private outputListeners: Array<() => void> = [];

  constructor(api: AppAPI, initialPath: string = '/') {
    this.id = `terminal-${Date.now()}-${Math.random()}`;
    this.api = api;
    this.fs = new FileSystemAdapter(api);
    this.ansiParser = new AnsiParser();
    this.currentPath = initialPath;

    // Set default environment variables
    this.environment.set('USER', 'user');
    this.environment.set('HOME', '/');
    this.environment.set('PATH', '/bin:/usr/bin');
    this.environment.set('TERM', 'xterm-256color');
  }

  /**
   * Initialize the session
   */
  async init(): Promise<void> {
    await this.fs.init();
    this.currentPath = '/';
  }

  /**
   * Get the file system adapter
   */
  getFileSystem(): FileSystemAdapter {
    return this.fs;
  }

  /**
   * Get the AppAPI instance
   */
  getAPI(): AppAPI {
    return this.api;
  }

  /**
   * Write text to output
   */
  write(text: string, style?: TextStyle): void {
    if (this.outputBuffer.length === 0) {
      // Create new line
      this.writeLine(text, style);
      return;
    }

    // Append to last line
    const lastLine = this.outputBuffer[this.outputBuffer.length - 1];
    lastLine.content += text;

    // Merge styles if needed
    if (style) {
      lastLine.style = { ...lastLine.style, ...style };
    }

    this.notifyOutputChange();
  }

  /**
   * Write a line to output
   */
  writeLine(text: string = '', style?: TextStyle): void {
    const line: OutputLine = {
      id: `line-${Date.now()}-${Math.random()}`,
      content: text,
      style,
      timestamp: Date.now(),
      type: 'output',
    };

    // Parse ANSI codes if present
    if (this.ansiParser.hasAnsiCodes(text)) {
      line.spans = this.ansiParser.parse(text);
    }

    this.outputBuffer.push(line);

    // Trim buffer if too large
    if (this.outputBuffer.length > this.maxOutputLines) {
      this.outputBuffer = this.outputBuffer.slice(-this.maxOutputLines);
    }

    this.notifyOutputChange();
  }

  /**
   * Write an error line
   */
  writeError(text: string): void {
    this.writeLine(text, { color: 'var(--terminal-error, #ff5555)' });
  }

  /**
   * Write a system line
   */
  writeSystem(text: string): void {
    this.writeLine(text, { color: 'var(--terminal-system, #ffcc00)' });
  }

  /**
   * Clear the screen
   */
  clearScreen(): void {
    this.outputBuffer = [];
    this.notifyOutputChange();
  }

  /**
   * Update the last line (for progress indicators)
   */
  updateLastLine(text: string, style?: TextStyle): void {
    if (this.outputBuffer.length === 0) {
      this.writeLine(text, style);
      return;
    }

    const lastLine = this.outputBuffer[this.outputBuffer.length - 1];
    lastLine.content = text;
    lastLine.style = style;

    // Re-parse ANSI if needed
    if (this.ansiParser.hasAnsiCodes(text)) {
      lastLine.spans = this.ansiParser.parse(text);
    }

    this.notifyOutputChange();
  }

  /**
   * Get current working directory
   */
  getWorkingDirectory(): string {
    return this.currentPath;
  }

  /**
   * Change working directory
   */
  async changeDirectory(path: string): Promise<void> {
    const resolvedPath = this.fs.resolvePath(path, this.currentPath);
    const node = await this.fs.findByPath(resolvedPath);

    if (!node) {
      throw new Error(`Directory not found: ${path}`);
    }

    if (node.type !== 'directory') {
      throw new Error(`Not a directory: ${path}`);
    }

    this.currentPath = resolvedPath;
    this.fs.setCurrentDirId(node.id);
  }

  /**
   * Get the prompt string
   */
  getPrompt(): string {
    // Replace variables in prompt template
    let prompt = this.promptTemplate;
    prompt = prompt.replace('~', this.currentPath === '/' ? '/' : this.currentPath);
    return prompt + ' ';
  }

  /**
   * Set the prompt template
   */
  setPrompt(template: string): void {
    this.promptTemplate = template;
  }

  /**
   * Add command to history
   */
  addToHistory(command: string): void {
    if (command.trim() === '') {
      return;
    }

    // Don't add duplicates of the last command
    if (this.commandHistory.length > 0 && this.commandHistory[this.commandHistory.length - 1] === command) {
      return;
    }

    this.commandHistory.push(command);

    // Trim history if too large
    if (this.commandHistory.length > this.maxHistorySize) {
      this.commandHistory = this.commandHistory.slice(-this.maxHistorySize);
    }

    // Reset history index
    this.historyIndex = this.commandHistory.length;
  }

  /**
   * Get command history
   */
  getHistory(): string[] {
    return [...this.commandHistory];
  }

  /**
   * Navigate command history
   */
  navigateHistory(direction: 'up' | 'down'): string | null {
    if (this.commandHistory.length === 0) {
      return null;
    }

    if (direction === 'up') {
      if (this.historyIndex > 0) {
        this.historyIndex--;
        return this.commandHistory[this.historyIndex];
      }
    } else {
      if (this.historyIndex < this.commandHistory.length - 1) {
        this.historyIndex++;
        return this.commandHistory[this.historyIndex];
      } else {
        this.historyIndex = this.commandHistory.length;
        return '';
      }
    }

    return null;
  }

  /**
   * Get environment variable
   */
  getEnv(key?: string): string | Map<string, string> {
    if (key === undefined) {
      return new Map(this.environment);
    }
    return this.environment.get(key) || '';
  }

  /**
   * Set environment variable
   */
  setEnv(key: string, value: string): void {
    this.environment.set(key, value);
  }

  /**
   * Delete environment variable
   */
  deleteEnv(key: string): void {
    this.environment.delete(key);
  }

  /**
   * Launch a terminal application
   */
  async launchApp(app: TerminalApplication): Promise<void> {
    this.currentApp = app;
    await app.onMount(this);
    // Application will render in the terminal until it returns false from onKeyPress
  }

  /**
   * Get current running application
   */
  getCurrentApp(): TerminalApplication | null {
    return this.currentApp;
  }

  /**
   * Exit current application
   */
  async exitApp(): Promise<void> {
    if (this.currentApp) {
      await this.currentApp.onUnmount();
      this.currentApp = null;
      this.notifyOutputChange();
    }
  }

  /**
   * Handle key press (for application mode)
   */
  async handleKeyPress(key: string, modifiers: {
    ctrl: boolean;
    alt: boolean;
    shift: boolean;
    meta: boolean;
  }): Promise<boolean> {
    if (this.currentApp) {
      const continueRunning = await this.currentApp.onKeyPress(key, modifiers);
      if (!continueRunning) {
        await this.exitApp();
      }
      return continueRunning;
    }
    return false;
  }

  /**
   * Add output change listener
   */
  onOutputChange(listener: () => void): () => void {
    this.outputListeners.push(listener);

    // Return unsubscribe function
    return () => {
      const index = this.outputListeners.indexOf(listener);
      if (index > -1) {
        this.outputListeners.splice(index, 1);
      }
    };
  }

  /**
   * Notify output change listeners
   */
  private notifyOutputChange(): void {
    this.outputListeners.forEach((listener) => listener());
  }

  /**
   * Read a line of input (for interactive commands)
   */
  async readLine(prompt?: string): Promise<string> {
    // Display the prompt if provided
    if (prompt) {
      this.write(prompt);
    }

    // Store the prompt for UI to use
    (this as any)._readLinePrompt = prompt || '';

    return new Promise((resolve) => {
      // Store the resolve function for the UI to call
      (this as any)._readLineResolve = resolve;
    });
  }

  /**
   * Check if we're waiting for readline input
   */
  isWaitingForReadLine(): boolean {
    return !!(this as any)._readLineResolve;
  }

  /**
   * Get the current readline prompt
   */
  getReadLinePrompt(): string {
    return (this as any)._readLinePrompt || '';
  }

  /**
   * Resolve the pending readLine promise
   */
  resolveReadLine(value: string): void {
    if ((this as any)._readLineResolve) {
      // Write the input to the output
      this.writeLine(value);

      (this as any)._readLineResolve(value);
      delete (this as any)._readLineResolve;
      delete (this as any)._readLinePrompt;
    }
  }

  /**
   * Wait for any key press
   */
  async waitForKey(): Promise<string> {
    return new Promise((resolve) => {
      (this as any)._waitForKeyResolve = resolve;
    });
  }

  /**
   * Resolve the pending waitForKey promise
   */
  resolveWaitForKey(key: string): void {
    if ((this as any)._waitForKeyResolve) {
      (this as any)._waitForKeyResolve(key);
      delete (this as any)._waitForKeyResolve;
    }
  }
}
