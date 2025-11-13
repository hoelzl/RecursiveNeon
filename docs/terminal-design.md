# Simulated Terminal Window - Design Document

## 1. Architecture Overview

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      TerminalApp Component                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              TerminalOutput (Display)                  │  │
│  │  - Scrollable output buffer                           │  │
│  │  - ANSI color rendering                               │  │
│  │  - Virtual scrolling for performance                  │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              TerminalInput (Input Line)                │  │
│  │  - Command input with cursor                          │  │
│  │  - Tab completion UI                                   │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  Uses:                                                       │
│  - TerminalSession (state management)                       │
│  - CommandRegistry (command lookup)                         │
│  - CompletionEngine (tab completion)                        │
│  - ThemeProvider (styling)                                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ uses
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     Core Terminal System                     │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │ TerminalSession  │  │ CommandRegistry  │               │
│  │                  │  │                  │               │
│  │ - Working dir    │  │ - Built-in cmds  │               │
│  │ - Command queue  │  │ - Custom cmds    │               │
│  │ - History        │  │ - Command lookup │               │
│  │ - Environment    │  │                  │               │
│  └──────────────────┘  └──────────────────┘               │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │ CompletionEngine │  │ OutputRenderer   │               │
│  │                  │  │                  │               │
│  │ - Path complete  │  │ - ANSI parser    │               │
│  │ - Command complete│  │ - Style builder │               │
│  │ - Custom complete │  │ - Line formatter│               │
│  └──────────────────┘  └──────────────────┘               │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ uses
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   File System & Backend                      │
│                                                              │
│  AppAPI.fs.*                                                │
│  - listDirectory()                                           │
│  - readFile()                                                │
│  - createFile()                                              │
│  - etc.                                                      │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Component Breakdown

#### 1.2.1 React Components

**TerminalApp** (`TerminalApp.tsx`)
- Main container component
- Manages terminal session lifecycle
- Handles window focus and blur events
- Coordinates between input and output components

**TerminalOutput** (`TerminalOutput.tsx`)
- Displays scrollable output buffer
- Renders ANSI-styled text
- Implements virtual scrolling for performance
- Auto-scrolls to bottom on new output

**TerminalInput** (`TerminalInput.tsx`)
- Handles keyboard input
- Displays prompt and current command
- Shows cursor and selection
- Displays completion suggestions

**TerminalThemeProvider** (`TerminalThemeProvider.tsx`)
- Wraps terminal with theme context
- Applies theme CSS variables
- Supports runtime theme switching

#### 1.2.2 Core Classes

**TerminalSession** (`terminal/TerminalSession.ts`)
```typescript
class TerminalSession {
  // Properties
  id: string;
  currentDirectory: string;
  commandHistory: string[];
  historyIndex: number;
  environment: Map<string, string>;
  outputBuffer: OutputLine[];

  // Methods
  executeCommand(command: string): Promise<void>;
  write(text: string, style?: TextStyle): void;
  writeLine(text: string, style?: TextStyle): void;
  changeDirectory(path: string): Promise<void>;
  getWorkingDirectory(): string;
  clearScreen(): void;
  addToHistory(command: string): void;
  navigateHistory(direction: 'up' | 'down'): string | null;
}
```

**CommandRegistry** (`terminal/CommandRegistry.ts`)
```typescript
interface Command {
  name: string;
  description: string;
  usage: string;
  options?: CommandOption[];
  execute: CommandExecutor;
  complete?: CompletionFunction;
}

interface CommandContext {
  session: TerminalSession;
  args: string[];
  options: Map<string, string | boolean>;
  rawInput: string;
  api: AppAPI;
}

type CommandExecutor = (context: CommandContext) => Promise<void> | void;
type CompletionFunction = (context: CompletionContext) => Promise<string[]>;

class CommandRegistry {
  private commands: Map<string, Command>;

  register(command: Command): void;
  unregister(commandName: string): void;
  get(commandName: string): Command | undefined;
  getAll(): Command[];
  execute(commandName: string, context: CommandContext): Promise<void>;
}
```

**CompletionEngine** (`terminal/CompletionEngine.ts`)
```typescript
interface CompletionContext {
  session: TerminalSession;
  commandLine: string;
  cursorPosition: number;
  api: AppAPI;
}

interface CompletionResult {
  completions: string[];
  prefix: string;
  suffix: string;
}

class CompletionEngine {
  constructor(private registry: CommandRegistry);

  async complete(context: CompletionContext): Promise<CompletionResult>;
  private completeCommand(partial: string): string[];
  private async completePath(partial: string, cwd: string): Promise<string[]>;
  private completeOption(command: string, partial: string): string[];
}
```

**OutputRenderer** (`terminal/OutputRenderer.ts`)
```typescript
interface TextStyle {
  color?: string;
  backgroundColor?: string;
  bold?: boolean;
  italic?: boolean;
  underline?: boolean;
  strikethrough?: boolean;
  dim?: boolean;
  inverse?: boolean;
}

interface OutputLine {
  id: string;
  content: string;
  style?: TextStyle;
  timestamp: number;
  type: 'output' | 'error' | 'input';
}

class OutputRenderer {
  parseANSI(text: string): StyledSpan[];
  buildStyles(style: TextStyle): React.CSSProperties;
  formatLine(line: OutputLine): React.ReactNode;
}
```

## 2. Detailed Component Design

### 2.1 TerminalApp Component

```typescript
// TerminalApp.tsx
import React, { useState, useRef, useEffect } from 'react';
import { TerminalSession } from '../terminal/TerminalSession';
import { CommandRegistry } from '../terminal/CommandRegistry';
import { TerminalOutput } from './TerminalOutput';
import { TerminalInput } from './TerminalInput';
import { TerminalThemeProvider } from './TerminalThemeProvider';
import { useWebSocket } from '../hooks/useWebSocket';
import { AppAPI } from '../utils/appApi';

interface TerminalAppProps {
  initialDirectory?: string;
  theme?: TerminalTheme;
  customCommands?: Command[];
}

export function TerminalApp({
  initialDirectory = '~',
  theme,
  customCommands = []
}: TerminalAppProps) {
  const wsClient = useWebSocket();
  const api = new AppAPI(wsClient);

  const [session] = useState(() => new TerminalSession(api, initialDirectory));
  const [registry] = useState(() => {
    const reg = new CommandRegistry();
    // Register built-in commands
    registerBuiltInCommands(reg);
    // Register custom commands
    customCommands.forEach(cmd => reg.register(cmd));
    return reg;
  });

  const [inputValue, setInputValue] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const outputRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Initialize session
    session.writeLine(`Welcome to RecursiveNeon Terminal v1.0`, {
      color: 'var(--accent-cyan)'
    });
    session.writeLine(`Type 'help' for available commands.`);
    session.writeLine('');
  }, [session]);

  const handleCommand = async (command: string) => {
    if (!command.trim()) {
      session.writeLine('');
      return;
    }

    // Echo command
    session.writeLine(`${session.getPrompt()} ${command}`, {
      color: 'var(--text-primary)'
    });

    // Add to history
    session.addToHistory(command);

    // Parse and execute
    const [commandName, ...args] = command.trim().split(/\s+/);

    try {
      await registry.execute(commandName, {
        session,
        args,
        options: parseOptions(args),
        rawInput: command,
        api
      });
    } catch (error) {
      session.writeLine(`Error: ${error.message}`, {
        color: 'var(--error-color)'
      });
    }

    // Clear input
    setInputValue('');
    setSuggestions([]);
  };

  const handleTabCompletion = async () => {
    const completions = await session.complete(inputValue, inputValue.length);

    if (completions.completions.length === 1) {
      // Single match - complete it
      setInputValue(completions.prefix + completions.completions[0] + completions.suffix);
    } else if (completions.completions.length > 1) {
      // Multiple matches - show suggestions
      setSuggestions(completions.completions);
    }
  };

  return (
    <TerminalThemeProvider theme={theme}>
      <div className="terminal-app">
        <TerminalOutput
          ref={outputRef}
          lines={session.outputBuffer}
        />
        <TerminalInput
          value={inputValue}
          onChange={setInputValue}
          onSubmit={handleCommand}
          onTabCompletion={handleTabCompletion}
          suggestions={suggestions}
          prompt={session.getPrompt()}
          session={session}
        />
      </div>
    </TerminalThemeProvider>
  );
}
```

### 2.2 Built-in Commands

All built-in commands follow a consistent pattern:

```typescript
// terminal/commands/ls.ts
import { Command, CommandContext } from '../CommandRegistry';

export const lsCommand: Command = {
  name: 'ls',
  description: 'List directory contents',
  usage: 'ls [OPTIONS] [PATH]',
  options: [
    { flag: '-l', description: 'Use long listing format' },
    { flag: '-a', description: 'Show hidden files' },
    { flag: '-h', description: 'Human-readable file sizes' },
  ],

  async execute(context: CommandContext) {
    const { session, args, options, api } = context;

    const path = args[0] || session.getWorkingDirectory();
    const longFormat = options.has('l');
    const showHidden = options.has('a');
    const humanReadable = options.has('h');

    try {
      const contents = await api.fs.listDirectory(path);

      if (longFormat) {
        // Display in long format
        contents.forEach(item => {
          const size = humanReadable
            ? formatBytes(item.size)
            : item.size.toString();
          const line = `${item.type === 'directory' ? 'd' : '-'} ${size.padStart(10)} ${item.name}`;
          session.writeLine(line, {
            color: item.type === 'directory'
              ? 'var(--accent-cyan)'
              : 'var(--text-primary)'
          });
        });
      } else {
        // Display in grid format
        const names = contents.map(item => {
          const name = item.name;
          return item.type === 'directory' ? name + '/' : name;
        });
        session.writeLine(formatGrid(names, 80));
      }
    } catch (error) {
      session.writeLine(`ls: cannot access '${path}': ${error.message}`, {
        color: 'var(--error-color)'
      });
    }
  },

  async complete(context) {
    // Complete file/directory paths
    return context.api.fs.completePathAsync(context.session.getWorkingDirectory());
  }
};
```

### 2.3 File System Integration

The terminal integrates with the existing file system through `AppAPI`:

```typescript
// terminal/FileSystemAdapter.ts
export class FileSystemAdapter {
  constructor(private api: AppAPI) {}

  async resolvePath(path: string, cwd: string): Promise<string> {
    if (path.startsWith('/')) {
      return path; // Absolute path
    } else if (path.startsWith('~')) {
      return path.replace('~', await this.getHomeDirectory());
    } else {
      return this.joinPaths(cwd, path);
    }
  }

  async listDirectory(path: string): Promise<FileNode[]> {
    const result = await this.api.send('fs.list', { path });
    return result.nodes;
  }

  async readFile(path: string): Promise<string> {
    const result = await this.api.send('fs.read', { path });
    return result.content;
  }

  async createFile(path: string, content: string): Promise<void> {
    await this.api.send('fs.create', { path, content, type: 'file' });
  }

  async createDirectory(path: string): Promise<void> {
    await this.api.send('fs.create', { path, type: 'directory' });
  }

  async delete(path: string, recursive: boolean = false): Promise<void> {
    await this.api.send('fs.delete', { path, recursive });
  }

  async move(source: string, destination: string): Promise<void> {
    await this.api.send('fs.move', { source, destination });
  }

  async copy(source: string, destination: string): Promise<void> {
    await this.api.send('fs.copy', { source, destination });
  }

  async exists(path: string): Promise<boolean> {
    try {
      await this.api.send('fs.stat', { path });
      return true;
    } catch {
      return false;
    }
  }

  async stat(path: string): Promise<FileStats> {
    return await this.api.send('fs.stat', { path });
  }
}
```

## 3. Extension API Design

### 3.1 Adding Custom Commands

Game developers can easily add custom commands:

```typescript
// Example: Adding a 'grep' command
import { Command, CommandContext } from './terminal/CommandRegistry';

const grepCommand: Command = {
  name: 'grep',
  description: 'Search for patterns in files',
  usage: 'grep [OPTIONS] PATTERN [FILE...]',
  options: [
    { flag: '-i', description: 'Ignore case' },
    { flag: '-n', description: 'Show line numbers' },
    { flag: '-r', description: 'Recursive search' },
  ],

  async execute(context: CommandContext) {
    const { session, args, options } = context;

    if (args.length < 1) {
      session.writeLine('Usage: grep [OPTIONS] PATTERN [FILE...]', {
        color: 'var(--error-color)'
      });
      return;
    }

    const pattern = args[0];
    const files = args.slice(1);
    const ignoreCase = options.has('i');
    const showLineNumbers = options.has('n');

    const regex = new RegExp(pattern, ignoreCase ? 'i' : '');

    for (const file of files) {
      const content = await context.api.fs.readFile(file);
      const lines = content.split('\n');

      lines.forEach((line, index) => {
        if (regex.test(line)) {
          const prefix = showLineNumbers ? `${index + 1}:` : '';
          session.writeLine(`${prefix}${line}`);
        }
      });
    }
  },

  async complete(context) {
    // Complete file paths
    return context.api.fs.completePathAsync(context.session.getWorkingDirectory());
  }
};

// Register the command
terminalSession.registry.register(grepCommand);
```

### 3.2 Creating Text-Based Applications

For full-screen applications like text editors:

```typescript
// terminal/TerminalApp.ts (interface for apps)
export interface TerminalApplication {
  name: string;
  onMount(session: TerminalSession): Promise<void>;
  onUnmount(): Promise<void>;
  onKeyPress(key: string, modifiers: KeyModifiers): Promise<boolean>;
  onResize(width: number, height: number): void;
  render(): string; // Returns the screen content
}

// Example: Simple text editor
class NanoEditor implements TerminalApplication {
  name = 'nano';
  private content: string[] = [];
  private cursorLine = 0;
  private cursorCol = 0;
  private filename: string;

  constructor(filename: string) {
    this.filename = filename;
  }

  async onMount(session: TerminalSession): Promise<void> {
    // Load file content
    const content = await session.api.fs.readFile(this.filename);
    this.content = content.split('\n');
  }

  async onUnmount(): Promise<void> {
    // Save file
    await this.session.api.fs.writeFile(
      this.filename,
      this.content.join('\n')
    );
  }

  async onKeyPress(key: string, modifiers: KeyModifiers): Promise<boolean> {
    if (modifiers.ctrl && key === 'x') {
      // Exit editor
      return false; // Return to terminal
    }

    if (modifiers.ctrl && key === 's') {
      // Save file
      await this.save();
      return true;
    }

    // Handle cursor movement, text editing, etc.
    // ...

    return true; // Continue running
  }

  onResize(width: number, height: number): void {
    // Handle terminal resize
  }

  render(): string {
    // Render the editor screen
    let screen = '';

    // Render content lines
    this.content.forEach((line, index) => {
      screen += line + '\n';
    });

    // Render status bar
    screen += '─'.repeat(80) + '\n';
    screen += `File: ${this.filename} | Line ${this.cursorLine + 1}/${this.content.length}`;

    return screen;
  }

  private async save(): Promise<void> {
    await this.session.api.fs.writeFile(
      this.filename,
      this.content.join('\n')
    );
  }
}

// Launch the editor from a command
const nanoCommand: Command = {
  name: 'nano',
  description: 'Simple text editor',
  usage: 'nano [FILE]',

  async execute(context: CommandContext) {
    if (context.args.length === 0) {
      context.session.writeLine('Usage: nano [FILE]');
      return;
    }

    const filename = context.args[0];
    const editor = new NanoEditor(filename);

    await context.session.launchApp(editor);
  }
};
```

### 3.3 Creating Mini-Games

For terminal-based mini-games (like Fallout's hacking mini-game):

```typescript
// Example: Word matching mini-game
class HackingMiniGame implements TerminalApplication {
  name = 'hack';
  private words: string[] = [];
  private correctWord: string;
  private attempts = 4;
  private guesses: Array<{ word: string; similarity: number }> = [];

  constructor(difficulty: number) {
    this.generatePuzzle(difficulty);
  }

  async onMount(session: TerminalSession): Promise<void> {
    session.clearScreen();
    this.renderGame(session);
  }

  async onUnmount(): Promise<void> {
    // Cleanup
  }

  async onKeyPress(key: string, modifiers: KeyModifiers): Promise<boolean> {
    // Handle input for word selection
    // Return false when game ends
    return true;
  }

  onResize(width: number, height: number): void {
    // Handle resize
  }

  render(): string {
    let screen = '';

    // Render header
    screen += '═══ ROBCO INDUSTRIES TERMLINK ═══\n';
    screen += `\nAttempts Remaining: ${'█'.repeat(this.attempts)}\n\n`;

    // Render word grid
    const cols = 2;
    const rows = Math.ceil(this.words.length / cols);

    for (let row = 0; row < rows; row++) {
      for (let col = 0; col < cols; col++) {
        const index = row + col * rows;
        if (index < this.words.length) {
          screen += this.words[index].padEnd(20);
        }
      }
      screen += '\n';
    }

    // Render previous guesses
    if (this.guesses.length > 0) {
      screen += '\n─────────────────────────────────\n';
      this.guesses.forEach(guess => {
        screen += `> ${guess.word}: ${guess.similarity}/${this.correctWord.length} correct\n`;
      });
    }

    return screen;
  }

  private generatePuzzle(difficulty: number): void {
    // Generate word list with similar patterns
    // Select correct word
    // ...
  }

  private checkWord(word: string): number {
    let matches = 0;
    for (let i = 0; i < word.length; i++) {
      if (word[i] === this.correctWord[i]) {
        matches++;
      }
    }
    return matches;
  }
}

// Launch from terminal
const hackCommand: Command = {
  name: 'hack',
  description: 'Start hacking mini-game',
  usage: 'hack [DIFFICULTY]',

  async execute(context: CommandContext) {
    const difficulty = parseInt(context.args[0]) || 1;
    const game = new HackingMiniGame(difficulty);

    await context.session.launchApp(game);
  }
};
```

## 4. Theming System

### 4.1 Theme Configuration

```typescript
// terminal/TerminalTheme.ts
export interface TerminalTheme {
  name: string;

  // Colors
  background: string;
  foreground: string;
  cursor: string;
  cursorAccent: string;
  selection: string;

  // ANSI Colors (0-15)
  black: string;
  red: string;
  green: string;
  yellow: string;
  blue: string;
  magenta: string;
  cyan: string;
  white: string;
  brightBlack: string;
  brightRed: string;
  brightGreen: string;
  brightYellow: string;
  brightBlue: string;
  brightMagenta: string;
  brightCyan: string;
  brightWhite: string;

  // Font
  fontFamily: string;
  fontSize: number;
  lineHeight: number;

  // Cursor
  cursorStyle: 'block' | 'underline' | 'bar';
  cursorBlink: boolean;

  // Effects
  opacity: number;
  blur: number;
}

// Predefined themes
export const themes = {
  cyberpunk: {
    name: 'Cyberpunk',
    background: '#0a0e27',
    foreground: '#00ffff',
    cursor: '#ff00ff',
    // ... (full color palette)
  },

  matrix: {
    name: 'Matrix',
    background: '#000000',
    foreground: '#00ff00',
    cursor: '#00ff00',
    // ...
  },

  retro: {
    name: 'Retro',
    background: '#000000',
    foreground: '#00ff00',
    cursor: '#00ff00',
    fontFamily: '"VT323", monospace',
    // ...
  },

  fallout: {
    name: 'Fallout',
    background: '#0c0c0c',
    foreground: '#00ff00',
    cursor: '#00ff00',
    // ...
  }
};
```

### 4.2 Applying Themes

```typescript
// TerminalThemeProvider.tsx
export function TerminalThemeProvider({
  theme,
  children
}: {
  theme?: TerminalTheme;
  children: React.ReactNode;
}) {
  const appliedTheme = theme || themes.cyberpunk;

  const style = {
    '--terminal-bg': appliedTheme.background,
    '--terminal-fg': appliedTheme.foreground,
    '--terminal-cursor': appliedTheme.cursor,
    '--terminal-font': appliedTheme.fontFamily,
    '--terminal-font-size': `${appliedTheme.fontSize}px`,
    '--terminal-line-height': appliedTheme.lineHeight,
    '--terminal-opacity': appliedTheme.opacity,
    // ... map all theme properties to CSS variables
  } as React.CSSProperties;

  return (
    <div className="terminal-theme" style={style}>
      {children}
    </div>
  );
}
```

## 5. Performance Optimizations

### 5.1 Virtual Scrolling

For handling large output buffers efficiently:

```typescript
// TerminalOutput.tsx
import { FixedSizeList as List } from 'react-window';

export function TerminalOutput({ lines }: { lines: OutputLine[] }) {
  const listRef = useRef<List>(null);

  useEffect(() => {
    // Auto-scroll to bottom when new lines are added
    if (listRef.current) {
      listRef.current.scrollToItem(lines.length - 1);
    }
  }, [lines.length]);

  const Row = ({ index, style }: { index: number; style: React.CSSProperties }) => {
    const line = lines[index];
    return (
      <div style={style} className="terminal-line">
        {renderLine(line)}
      </div>
    );
  };

  return (
    <List
      ref={listRef}
      height={600}
      itemCount={lines.length}
      itemSize={20}
      width="100%"
    >
      {Row}
    </List>
  );
}
```

### 5.2 Command Debouncing

Prevent command spam:

```typescript
class CommandThrottle {
  private lastExecution = 0;
  private readonly minInterval = 100; // ms

  async execute(fn: () => Promise<void>): Promise<void> {
    const now = Date.now();
    if (now - this.lastExecution < this.minInterval) {
      return; // Skip execution
    }

    this.lastExecution = now;
    await fn();
  }
}
```

## 6. Testing Strategy

### 6.1 Unit Tests

```typescript
// __tests__/CommandRegistry.test.ts
describe('CommandRegistry', () => {
  it('should register and retrieve commands', () => {
    const registry = new CommandRegistry();
    const cmd = { name: 'test', execute: jest.fn() };

    registry.register(cmd);
    expect(registry.get('test')).toBe(cmd);
  });

  it('should execute registered commands', async () => {
    const registry = new CommandRegistry();
    const execute = jest.fn();
    registry.register({ name: 'test', execute });

    await registry.execute('test', mockContext);
    expect(execute).toHaveBeenCalled();
  });
});

// __tests__/CompletionEngine.test.ts
describe('CompletionEngine', () => {
  it('should complete command names', async () => {
    const engine = new CompletionEngine(registry);
    const result = await engine.complete({
      commandLine: 'l',
      cursorPosition: 1,
      session: mockSession
    });

    expect(result.completions).toContain('ls');
  });

  it('should complete file paths', async () => {
    // Test path completion
  });
});
```

## 7. File Structure

```
frontend/src/
├── components/
│   ├── apps/
│   │   └── TerminalApp.tsx          # Main terminal component
│   ├── terminal/
│   │   ├── TerminalOutput.tsx       # Output display
│   │   ├── TerminalInput.tsx        # Input handler
│   │   ├── TerminalThemeProvider.tsx # Theme wrapper
│   │   └── TerminalLine.tsx         # Single line renderer
│   └── ...
├── terminal/
│   ├── core/
│   │   ├── TerminalSession.ts       # Session management
│   │   ├── CommandRegistry.ts       # Command registration
│   │   ├── CompletionEngine.ts      # Tab completion
│   │   ├── OutputRenderer.ts        # ANSI rendering
│   │   └── FileSystemAdapter.ts     # FS operations
│   ├── commands/
│   │   ├── index.ts                 # Export all commands
│   │   ├── ls.ts
│   │   ├── cd.ts
│   │   ├── cat.ts
│   │   ├── mkdir.ts
│   │   ├── rm.ts
│   │   ├── mv.ts
│   │   ├── cp.ts
│   │   ├── pwd.ts
│   │   ├── echo.ts
│   │   ├── clear.ts
│   │   ├── help.ts
│   │   ├── man.ts
│   │   └── history.ts
│   ├── apps/
│   │   ├── TerminalApplication.ts   # App interface
│   │   └── examples/
│   │       ├── NanoEditor.ts        # Example editor
│   │       └── HackingGame.ts       # Example game
│   ├── themes/
│   │   ├── TerminalTheme.ts         # Theme interface
│   │   └── presets.ts               # Built-in themes
│   └── utils/
│       ├── ansiParser.ts            # Parse ANSI codes
│       ├── pathUtils.ts             # Path manipulation
│       └── textFormatter.ts         # Text formatting
├── styles/
│   └── terminal.css                 # Terminal styles
└── ...
```

## 8. Usage Examples

### 8.1 Basic Terminal Usage

```typescript
// In Desktop.tsx or game initialization
const terminalAction = () => {
  openWindow({
    title: 'Terminal',
    type: 'terminal',
    content: <TerminalApp />,
    position: { x: 100, y: 100 },
    size: { width: 800, height: 600 },
    minimized: false,
  });
};
```

### 8.2 Terminal with Custom Commands

```typescript
const customCommands = [
  grepCommand,
  vimCommand,
  hackCommand,
];

<TerminalApp
  initialDirectory="/home/user"
  customCommands={customCommands}
  theme={themes.cyberpunk}
/>
```

### 8.3 Themed Terminal for Different Games

```typescript
// Cyberpunk game
<TerminalApp theme={themes.cyberpunk} />

// Retro/Fallout style game
<TerminalApp theme={themes.fallout} />

// Custom theme
<TerminalApp theme={{
  name: 'Custom',
  background: '#1a1a2e',
  foreground: '#eee',
  // ... custom colors
}} />
```

## 9. Future Enhancements

### Phase 2 Features
1. **Pipe Support**: Chain commands with `|`
2. **Redirection**: Support `>`, `>>`, `<`
3. **Environment Variables**: `export VAR=value`, `$VAR` expansion
4. **Shell Scripts**: Execute `.sh` files
5. **Background Jobs**: `&`, `bg`, `fg`, `jobs`

### Phase 3 Features
1. **Split Panes**: Multiple terminal panes in one window
2. **Tabs**: Multiple terminal tabs
3. **Session Persistence**: Save/restore terminal state
4. **Terminal Recording**: Record and replay sessions
5. **SSH-like**: Connect to other in-game systems

## 10. Summary

This design provides:

✅ **Extensible command system** - Easy to add custom commands
✅ **Full-screen app support** - Host text editors, games, etc.
✅ **Rich theming** - Multiple colors, fonts, styles
✅ **High performance** - Virtual scrolling, optimized rendering
✅ **Familiar interface** - Bash-like syntax and behavior
✅ **Clean architecture** - Modular, testable, maintainable
✅ **Type-safe** - Full TypeScript support
✅ **Well-integrated** - Works with existing window and file systems

The API is simple enough for game developers to extend, yet powerful enough to build complex terminal-based applications and mini-games.
