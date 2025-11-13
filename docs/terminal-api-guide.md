# Terminal System - Client API Guide

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Basic Usage](#2-basic-usage)
3. [Adding Custom Commands](#3-adding-custom-commands)
4. [Creating Text Applications](#4-creating-text-applications)
5. [Building Mini-Games](#5-building-mini-games)
6. [Theming and Styling](#6-theming-and-styling)
7. [Advanced Features](#7-advanced-features)
8. [Best Practices](#8-best-practices)
9. [API Reference](#9-api-reference)

---

## 1. Getting Started

### 1.1 Opening a Terminal Window

The simplest way to open a terminal:

```typescript
import { useGameStore } from './stores/gameStore';
import { TerminalApp } from './components/apps/TerminalApp';

function MyComponent() {
  const { openWindow } = useGameStore();

  const openTerminal = () => {
    openWindow({
      title: 'Terminal',
      type: 'terminal',
      content: <TerminalApp />,
      position: { x: 100, y: 100 },
      size: { width: 800, height: 600 },
      minimized: false,
    });
  };

  return (
    <button onClick={openTerminal}>
      Open Terminal
    </button>
  );
}
```

### 1.2 Terminal with Custom Configuration

```typescript
import { TerminalApp } from './components/apps/TerminalApp';
import { themes } from './terminal/themes/presets';

<TerminalApp
  initialDirectory="/home/user"
  theme={themes.cyberpunk}
  customCommands={myCommands}
  prompt="player@game:~$"
/>
```

---

## 2. Basic Usage

### 2.1 Built-in Commands

The terminal comes with standard Unix-like commands:

| Command | Description | Example |
|---------|-------------|---------|
| `ls` | List files | `ls -la /home` |
| `cd` | Change directory | `cd documents` |
| `pwd` | Print working directory | `pwd` |
| `cat` | Display file contents | `cat readme.txt` |
| `mkdir` | Create directory | `mkdir -p dir/subdir` |
| `rm` | Remove files | `rm -rf temp/` |
| `mv` | Move/rename files | `mv old.txt new.txt` |
| `cp` | Copy files | `cp -r src/ dest/` |
| `touch` | Create empty file | `touch newfile.txt` |
| `echo` | Print text | `echo "Hello World"` |
| `clear` | Clear screen | `clear` |
| `help` | Show commands | `help` |
| `man` | Command manual | `man ls` |
| `history` | Command history | `history` |

### 2.2 Interacting with the File System

The terminal integrates with your game's simulated file system:

```typescript
// Files created in the terminal are accessible via the file system API
// and vice versa

// In terminal:
// $ mkdir documents
// $ cd documents
// $ echo "secret data" > password.txt

// In your game code:
const api = new AppAPI(wsClient);
const file = await api.fs.readFile('/home/user/documents/password.txt');
console.log(file.content); // "secret data"
```

---

## 3. Adding Custom Commands

### 3.1 Simple Command

Create a custom command that doesn't interact with files:

```typescript
import { Command } from './terminal/core/CommandRegistry';

const fortuneCommand: Command = {
  name: 'fortune',
  description: 'Display a random fortune',
  usage: 'fortune',

  execute(context) {
    const fortunes = [
      'You will find success in unexpected places.',
      'A bug-free program is a myth.',
      'The best code is no code at all.',
      'Today is a good day to refactor.',
    ];

    const randomFortune = fortunes[Math.floor(Math.random() * fortunes.length)];

    context.session.writeLine(randomFortune, {
      color: 'var(--accent-cyan)',
      italic: true
    });
  }
};

// Register it:
<TerminalApp customCommands={[fortuneCommand]} />
```

### 3.2 Command with Arguments

```typescript
const sayCommand: Command = {
  name: 'say',
  description: 'Make the computer speak',
  usage: 'say <message>',

  execute(context) {
    if (context.args.length === 0) {
      context.session.writeLine('Usage: say <message>', {
        color: 'var(--error-color)'
      });
      return;
    }

    const message = context.args.join(' ');

    context.session.writeLine(`Computer says: "${message}"`, {
      color: 'var(--accent-magenta)',
      bold: true
    });

    // You could also trigger game events here
    // gameEvents.emit('computer-spoke', message);
  }
};
```

### 3.3 Command with Options/Flags

```typescript
const listCommand: Command = {
  name: 'tasks',
  description: 'List game tasks',
  usage: 'tasks [OPTIONS]',
  options: [
    { flag: '-a', description: 'Show all tasks including completed' },
    { flag: '-p', description: 'Show only priority tasks' },
  ],

  execute(context) {
    const { session, options } = context;
    const showAll = options.has('a');
    const priorityOnly = options.has('p');

    // Fetch tasks from game state
    const tasks = gameState.getTasks();

    let filtered = tasks;
    if (!showAll) {
      filtered = filtered.filter(t => !t.completed);
    }
    if (priorityOnly) {
      filtered = filtered.filter(t => t.priority === 'high');
    }

    if (filtered.length === 0) {
      session.writeLine('No tasks found.');
      return;
    }

    filtered.forEach((task, index) => {
      const status = task.completed ? '✓' : ' ';
      const priority = task.priority === 'high' ? '!' : ' ';

      session.writeLine(`[${status}] ${priority} ${task.title}`, {
        color: task.completed
          ? 'var(--text-secondary)'
          : 'var(--text-primary)'
      });
    });
  }
};
```

### 3.4 Async Command (with File System)

```typescript
const searchCommand: Command = {
  name: 'search',
  description: 'Search for files containing text',
  usage: 'search <pattern> <directory>',

  async execute(context) {
    const { session, args, api } = context;

    if (args.length < 2) {
      session.writeLine('Usage: search <pattern> <directory>', {
        color: 'var(--error-color)'
      });
      return;
    }

    const [pattern, directory] = args;
    const regex = new RegExp(pattern, 'i');

    session.writeLine(`Searching for "${pattern}" in ${directory}...`);

    try {
      // List all files recursively
      const files = await api.fs.listRecursive(directory);

      let foundCount = 0;

      for (const file of files) {
        if (file.type === 'file') {
          const content = await api.fs.readFile(file.path);

          if (regex.test(content)) {
            foundCount++;
            session.writeLine(`  ${file.path}`, {
              color: 'var(--accent-cyan)'
            });
          }
        }
      }

      session.writeLine(`\nFound ${foundCount} matching file(s).`);

    } catch (error) {
      session.writeLine(`Error: ${error.message}`, {
        color: 'var(--error-color)'
      });
    }
  },

  // Add tab completion for directory paths
  async complete(context) {
    const { session, api } = context;
    const cwd = session.getWorkingDirectory();

    // Complete directory paths
    const dirs = await api.fs.listDirectory(cwd);
    return dirs
      .filter(d => d.type === 'directory')
      .map(d => d.name);
  }
};
```

### 3.5 Command with Custom Completion

```typescript
const connectCommand: Command = {
  name: 'connect',
  description: 'Connect to a remote server',
  usage: 'connect <server>',

  async execute(context) {
    const { session, args } = context;
    const server = args[0];

    if (!server) {
      session.writeLine('Usage: connect <server>', {
        color: 'var(--error-color)'
      });
      return;
    }

    session.writeLine(`Connecting to ${server}...`);

    // Simulate connection
    await new Promise(resolve => setTimeout(resolve, 1000));

    session.writeLine(`Connected to ${server}`, {
      color: 'var(--accent-green)'
    });

    // Update game state
    gameState.connectedServer = server;
  },

  // Custom completion for server names
  async complete(context) {
    // Return list of available servers
    const servers = [
      'mainframe.corp.local',
      'database.internal',
      'backup.remote',
      'admin.secure',
    ];

    return servers;
  }
};
```

---

## 4. Creating Text Applications

### 4.1 Application Interface

Text applications take over the full terminal display:

```typescript
import { TerminalApplication, TerminalSession } from './terminal/core';

export interface TerminalApplication {
  name: string;
  onMount(session: TerminalSession): Promise<void>;
  onUnmount(): Promise<void>;
  onKeyPress(key: string, modifiers: KeyModifiers): Promise<boolean>;
  onResize?(width: number, height: number): void;
  render(): string;
}

export interface KeyModifiers {
  ctrl: boolean;
  alt: boolean;
  shift: boolean;
  meta: boolean;
}
```

### 4.2 Simple Text Editor

```typescript
class SimpleEditor implements TerminalApplication {
  name = 'edit';

  private lines: string[] = [];
  private cursorLine = 0;
  private cursorCol = 0;
  private filename: string;
  private session: TerminalSession;
  private modified = false;

  constructor(filename: string) {
    this.filename = filename;
  }

  async onMount(session: TerminalSession): Promise<void> {
    this.session = session;

    try {
      // Load file if it exists
      const content = await session.api.fs.readFile(this.filename);
      this.lines = content.split('\n');
    } catch {
      // File doesn't exist, start with empty content
      this.lines = [''];
    }
  }

  async onUnmount(): Promise<void> {
    if (this.modified) {
      // Save file on exit
      await this.save();
    }
  }

  async onKeyPress(key: string, modifiers: KeyModifiers): Promise<boolean> {
    // Ctrl+X - Exit
    if (modifiers.ctrl && key === 'x') {
      if (this.modified) {
        this.session.writeLine('Save changes? (y/n)', {
          color: 'var(--accent-yellow)'
        });
        // Handle confirmation...
      }
      return false; // Exit app, return to terminal
    }

    // Ctrl+S - Save
    if (modifiers.ctrl && key === 's') {
      await this.save();
      return true;
    }

    // Arrow keys - Move cursor
    if (key === 'ArrowUp' && this.cursorLine > 0) {
      this.cursorLine--;
      this.cursorCol = Math.min(this.cursorCol, this.lines[this.cursorLine].length);
      return true;
    }

    if (key === 'ArrowDown' && this.cursorLine < this.lines.length - 1) {
      this.cursorLine++;
      this.cursorCol = Math.min(this.cursorCol, this.lines[this.cursorLine].length);
      return true;
    }

    if (key === 'ArrowLeft' && this.cursorCol > 0) {
      this.cursorCol--;
      return true;
    }

    if (key === 'ArrowRight' && this.cursorCol < this.lines[this.cursorLine].length) {
      this.cursorCol++;
      return true;
    }

    // Enter - New line
    if (key === 'Enter') {
      const currentLine = this.lines[this.cursorLine];
      const before = currentLine.substring(0, this.cursorCol);
      const after = currentLine.substring(this.cursorCol);

      this.lines[this.cursorLine] = before;
      this.lines.splice(this.cursorLine + 1, 0, after);

      this.cursorLine++;
      this.cursorCol = 0;
      this.modified = true;
      return true;
    }

    // Backspace - Delete character
    if (key === 'Backspace') {
      if (this.cursorCol > 0) {
        const line = this.lines[this.cursorLine];
        this.lines[this.cursorLine] =
          line.substring(0, this.cursorCol - 1) +
          line.substring(this.cursorCol);
        this.cursorCol--;
        this.modified = true;
      } else if (this.cursorLine > 0) {
        // Merge with previous line
        const currentLine = this.lines[this.cursorLine];
        this.cursorLine--;
        this.cursorCol = this.lines[this.cursorLine].length;
        this.lines[this.cursorLine] += currentLine;
        this.lines.splice(this.cursorLine + 1, 1);
        this.modified = true;
      }
      return true;
    }

    // Regular character input
    if (key.length === 1) {
      const line = this.lines[this.cursorLine];
      this.lines[this.cursorLine] =
        line.substring(0, this.cursorCol) +
        key +
        line.substring(this.cursorCol);
      this.cursorCol++;
      this.modified = true;
      return true;
    }

    return true;
  }

  render(): string {
    let output = '';

    // Render header
    output += `┌─ ${this.filename} ${this.modified ? '[Modified]' : ''}`.padEnd(80, '─') + '┐\n';

    // Render lines (with line numbers)
    this.lines.forEach((line, index) => {
      const lineNum = (index + 1).toString().padStart(4, ' ');
      output += `${lineNum} │ ${line}\n`;

      // Render cursor on current line
      if (index === this.cursorLine) {
        const cursorPos = 7 + this.cursorCol; // Account for line number
        output += ' '.repeat(cursorPos) + '▂\n';
      }
    });

    // Render footer/status bar
    output += '└' + '─'.repeat(78) + '┘\n';
    output += ` Line ${this.cursorLine + 1}/${this.lines.length}, Col ${this.cursorCol + 1} `;
    output += `| Ctrl+S: Save | Ctrl+X: Exit`;

    return output;
  }

  private async save(): Promise<void> {
    const content = this.lines.join('\n');
    await this.session.api.fs.writeFile(this.filename, content);
    this.modified = false;
    this.session.writeLine('File saved.', {
      color: 'var(--accent-green)'
    });
  }
}

// Command to launch the editor
const editCommand: Command = {
  name: 'edit',
  description: 'Simple text editor',
  usage: 'edit <filename>',

  async execute(context) {
    if (context.args.length === 0) {
      context.session.writeLine('Usage: edit <filename>', {
        color: 'var(--error-color)'
      });
      return;
    }

    const filename = context.args[0];
    const editor = new SimpleEditor(filename);

    await context.session.launchApp(editor);
  }
};
```

### 4.3 File Viewer/Browser

```typescript
class FileBrowser implements TerminalApplication {
  name = 'browse';

  private currentDir: string;
  private files: FileNode[] = [];
  private selectedIndex = 0;
  private session: TerminalSession;

  constructor(initialDir: string = '~') {
    this.currentDir = initialDir;
  }

  async onMount(session: TerminalSession): Promise<void> {
    this.session = session;
    await this.loadDirectory();
  }

  async onUnmount(): Promise<void> {
    // Cleanup
  }

  async onKeyPress(key: string, modifiers: KeyModifiers): Promise<boolean> {
    // Q - Quit
    if (key === 'q' || key === 'Q') {
      return false;
    }

    // Arrow Up/Down - Navigate
    if (key === 'ArrowUp' && this.selectedIndex > 0) {
      this.selectedIndex--;
      return true;
    }

    if (key === 'ArrowDown' && this.selectedIndex < this.files.length - 1) {
      this.selectedIndex++;
      return true;
    }

    // Enter - Open file/directory
    if (key === 'Enter') {
      const selected = this.files[this.selectedIndex];

      if (selected.type === 'directory') {
        this.currentDir = selected.path;
        await this.loadDirectory();
        this.selectedIndex = 0;
      } else {
        // View file
        await this.viewFile(selected);
      }
      return true;
    }

    // Backspace - Go up
    if (key === 'Backspace') {
      const parent = this.currentDir.split('/').slice(0, -1).join('/') || '/';
      this.currentDir = parent;
      await this.loadDirectory();
      this.selectedIndex = 0;
      return true;
    }

    return true;
  }

  render(): string {
    let output = '';

    // Header
    output += `┌─ File Browser: ${this.currentDir} `.padEnd(80, '─') + '┐\n';
    output += '│'.padEnd(80) + '│\n';

    // File list
    this.files.forEach((file, index) => {
      const isSelected = index === this.selectedIndex;
      const icon = file.type === 'directory' ? '📁' : '📄';
      const prefix = isSelected ? '▶' : ' ';

      const line = ` ${prefix} ${icon} ${file.name}`;

      output += `│ ${line.padEnd(77)} │\n`;
    });

    // Fill empty space
    const remaining = 20 - this.files.length;
    for (let i = 0; i < remaining; i++) {
      output += '│'.padEnd(80) + '│\n';
    }

    // Footer
    output += '└' + '─'.repeat(78) + '┘\n';
    output += ' ↑/↓: Navigate | Enter: Open | Backspace: Up | Q: Quit';

    return output;
  }

  private async loadDirectory(): Promise<void> {
    this.files = await this.session.api.fs.listDirectory(this.currentDir);
  }

  private async viewFile(file: FileNode): Promise<void> {
    const content = await this.session.api.fs.readFile(file.path);

    this.session.writeLine(`\n─── ${file.name} ─────────────────────────`, {
      color: 'var(--accent-cyan)'
    });
    this.session.writeLine(content);
    this.session.writeLine('─'.repeat(40), {
      color: 'var(--accent-cyan)'
    });
    this.session.writeLine('\nPress any key to continue...');

    // Wait for key press
    await this.session.waitForKey();
  }
}
```

---

## 5. Building Mini-Games

### 5.1 Word Guessing Game

```typescript
class WordGuessGame implements TerminalApplication {
  name = 'wordguess';

  private wordList = ['TERMINAL', 'COMMAND', 'SYSTEM', 'NETWORK', 'DATABASE'];
  private targetWord: string;
  private guessedLetters: Set<string> = new Set();
  private attemptsLeft = 6;
  private session: TerminalSession;

  constructor() {
    this.targetWord = this.wordList[Math.floor(Math.random() * this.wordList.length)];
  }

  async onMount(session: TerminalSession): Promise<void> {
    this.session = session;
    session.writeLine('Welcome to Word Guess!', {
      color: 'var(--accent-cyan)',
      bold: true
    });
    session.writeLine('Guess the word one letter at a time.\n');
  }

  async onUnmount(): Promise<void> {}

  async onKeyPress(key: string, modifiers: KeyModifiers): Promise<boolean> {
    // ESC - Quit
    if (key === 'Escape') {
      return false;
    }

    // Only accept letters
    if (!/^[a-zA-Z]$/.test(key)) {
      return true;
    }

    const letter = key.toUpperCase();

    // Already guessed?
    if (this.guessedLetters.has(letter)) {
      return true;
    }

    this.guessedLetters.add(letter);

    // Check if letter is in word
    if (!this.targetWord.includes(letter)) {
      this.attemptsLeft--;
    }

    // Check win/lose
    if (this.isWordComplete()) {
      this.session.writeLine('\n🎉 You won! The word was ' + this.targetWord, {
        color: 'var(--accent-green)',
        bold: true
      });
      await this.session.waitForKey();
      return false;
    }

    if (this.attemptsLeft === 0) {
      this.session.writeLine('\n💀 Game Over! The word was ' + this.targetWord, {
        color: 'var(--accent-red)',
        bold: true
      });
      await this.session.waitForKey();
      return false;
    }

    return true;
  }

  render(): string {
    let output = '';

    // Title
    output += '╔═══════════════════════════════════════════════════════╗\n';
    output += '║              🎮 WORD GUESS GAME 🎮                   ║\n';
    output += '╚═══════════════════════════════════════════════════════╝\n\n';

    // Attempts
    output += `Attempts left: ${'❤️'.repeat(this.attemptsLeft)}\n\n`;

    // Word display
    output += '  ';
    for (const letter of this.targetWord) {
      if (this.guessedLetters.has(letter)) {
        output += letter + ' ';
      } else {
        output += '_ ';
      }
    }
    output += '\n\n';

    // Guessed letters
    const guessed = Array.from(this.guessedLetters).sort().join(' ');
    output += `Guessed: ${guessed}\n\n`;

    // Instructions
    output += '─'.repeat(60) + '\n';
    output += 'Type a letter to guess | ESC to quit\n';

    return output;
  }

  private isWordComplete(): boolean {
    for (const letter of this.targetWord) {
      if (!this.guessedLetters.has(letter)) {
        return false;
      }
    }
    return true;
  }
}

// Command to launch game
const wordguessCommand: Command = {
  name: 'wordguess',
  description: 'Play word guessing game',
  usage: 'wordguess',

  async execute(context) {
    const game = new WordGuessGame();
    await context.session.launchApp(game);
  }
};
```

### 5.2 Fallout-Style Hacking Game

```typescript
class HackingGame implements TerminalApplication {
  name = 'hack';

  private words: string[] = [];
  private correctWord: string;
  private attempts = 4;
  private guesses: Array<{ word: string; similarity: number }> = [];
  private hexAddresses: string[] = [];
  private solved = false;
  private session: TerminalSession;

  constructor(difficulty: number = 1) {
    this.generatePuzzle(difficulty);
  }

  async onMount(session: TerminalSession): Promise<void> {
    this.session = session;
  }

  async onUnmount(): Promise<void> {}

  async onKeyPress(key: string, modifiers: KeyModifiers): Promise<boolean> {
    if (this.solved || this.attempts === 0) {
      return false; // Game over
    }

    // Number keys 1-9 to select word
    const num = parseInt(key);
    if (!isNaN(num) && num >= 1 && num <= this.words.length) {
      const word = this.words[num - 1];
      await this.guessWord(word);
      return true;
    }

    return true;
  }

  render(): string {
    let output = '';

    // Header
    output += '╔═══════════════════════════════════════════════════════╗\n';
    output += '║          ROBCO INDUSTRIES (TM) TERMLINK               ║\n';
    output += '╠═══════════════════════════════════════════════════════╣\n';
    output += '║                  PASSWORD REQUIRED                    ║\n';
    output += '╚═══════════════════════════════════════════════════════╝\n\n';

    // Attempts remaining
    output += `ATTEMPTS REMAINING: ${'▓'.repeat(this.attempts)} ${'░'.repeat(4 - this.attempts)}\n\n`;

    // Display words in two columns with hex addresses
    const colWidth = 25;
    const rows = Math.ceil(this.words.length / 2);

    for (let i = 0; i < rows; i++) {
      const leftIndex = i;
      const rightIndex = i + rows;

      // Left column
      if (leftIndex < this.words.length) {
        const leftAddr = this.hexAddresses[leftIndex];
        const leftWord = this.words[leftIndex];
        const leftNum = (leftIndex + 1).toString();
        output += `${leftNum}) ${leftAddr}  ${leftWord}`.padEnd(colWidth);
      } else {
        output += ''.padEnd(colWidth);
      }

      // Right column
      if (rightIndex < this.words.length) {
        const rightAddr = this.hexAddresses[rightIndex];
        const rightWord = this.words[rightIndex];
        const rightNum = (rightIndex + 1).toString();
        output += `${rightNum}) ${rightAddr}  ${rightWord}`;
      }

      output += '\n';
    }

    output += '\n' + '─'.repeat(60) + '\n';

    // Display previous guesses
    if (this.guesses.length > 0) {
      output += '\nGUESS HISTORY:\n';
      this.guesses.forEach(guess => {
        output += `> ${guess.word}: ${guess.similarity}/${this.correctWord.length} correct\n`;
      });
    }

    output += '\nType number (1-' + this.words.length + ') to guess password\n';

    return output;
  }

  private generatePuzzle(difficulty: number): void {
    // Word length based on difficulty
    const length = 6 + difficulty;

    // Generate word list
    const wordBank = [
      'TERMINAL', 'PASSWORD', 'SECURITY', 'DATABASE',
      'NETWORK', 'FIREWALL', 'PROTOCOL', 'SYSTEM',
      'COMMAND', 'CIRCUIT', 'MATRIX', 'CYPHER'
    ];

    // Filter by length
    const filtered = wordBank.filter(w => w.length === length);

    // Select random words
    const count = Math.min(8, filtered.length);
    this.words = [];
    while (this.words.length < count) {
      const word = filtered[Math.floor(Math.random() * filtered.length)];
      if (!this.words.includes(word)) {
        this.words.push(word);
      }
    }

    // Select correct word
    this.correctWord = this.words[Math.floor(Math.random() * this.words.length)];

    // Generate hex addresses
    this.hexAddresses = this.words.map(() => {
      const addr = Math.floor(Math.random() * 0xFFFF);
      return '0x' + addr.toString(16).toUpperCase().padStart(4, '0');
    });
  }

  private async guessWord(word: string): Promise<void> {
    if (word === this.correctWord) {
      // Success!
      this.solved = true;
      this.session.writeLine('\n>ACCESS GRANTED<', {
        color: 'var(--accent-green)',
        bold: true
      });
      this.session.writeLine('Password accepted. Welcome, user.', {
        color: 'var(--accent-green)'
      });

      // Trigger game event
      // gameEvents.emit('hack-success');

      await this.session.waitForKey();
    } else {
      // Wrong guess
      const similarity = this.calculateSimilarity(word, this.correctWord);
      this.guesses.push({ word, similarity });
      this.attempts--;

      if (this.attempts === 0) {
        this.session.writeLine('\n>ACCESS DENIED<', {
          color: 'var(--accent-red)',
          bold: true
        });
        this.session.writeLine('Terminal locked. Try again later.', {
          color: 'var(--accent-red)'
        });

        // Trigger game event
        // gameEvents.emit('hack-failure');

        await this.session.waitForKey();
      }
    }
  }

  private calculateSimilarity(word1: string, word2: string): number {
    let matches = 0;
    for (let i = 0; i < word1.length; i++) {
      if (word1[i] === word2[i]) {
        matches++;
      }
    }
    return matches;
  }
}

// Command to launch hacking game
const hackCommand: Command = {
  name: 'hack',
  description: 'Hack into a secure system',
  usage: 'hack [difficulty]',

  async execute(context) {
    const difficulty = parseInt(context.args[0]) || 1;

    if (difficulty < 1 || difficulty > 5) {
      context.session.writeLine('Difficulty must be between 1 and 5', {
        color: 'var(--error-color)'
      });
      return;
    }

    const game = new HackingGame(difficulty);
    await context.session.launchApp(game);
  }
};
```

---

## 6. Theming and Styling

### 6.1 Using Built-in Themes

```typescript
import { themes } from './terminal/themes/presets';

// Cyberpunk theme (default)
<TerminalApp theme={themes.cyberpunk} />

// Matrix theme (green on black)
<TerminalApp theme={themes.matrix} />

// Retro terminal theme
<TerminalApp theme={themes.retro} />

// Fallout theme
<TerminalApp theme={themes.fallout} />
```

### 6.2 Creating Custom Themes

```typescript
import { TerminalTheme } from './terminal/themes/TerminalTheme';

const myCustomTheme: TerminalTheme = {
  name: 'Custom Neon',

  // Base colors
  background: '#1a1a2e',
  foreground: '#eee',
  cursor: '#ff00ff',
  cursorAccent: '#00ffff',
  selection: 'rgba(255, 255, 255, 0.2)',

  // ANSI colors (0-15)
  black: '#000000',
  red: '#ff5555',
  green: '#50fa7b',
  yellow: '#f1fa8c',
  blue: '#bd93f9',
  magenta: '#ff79c6',
  cyan: '#8be9fd',
  white: '#bbbbbb',
  brightBlack: '#555555',
  brightRed: '#ff8888',
  brightGreen: '#88ffaa',
  brightYellow: '#ffff88',
  brightBlue: '#ddaaff',
  brightMagenta: '#ffaadd',
  brightCyan: '#aaffff',
  brightWhite: '#ffffff',

  // Font
  fontFamily: '"Fira Code", "Courier New", monospace',
  fontSize: 14,
  lineHeight: 1.5,

  // Cursor
  cursorStyle: 'block',
  cursorBlink: true,

  // Effects
  opacity: 0.95,
  blur: 2,
};

// Use your custom theme
<TerminalApp theme={myCustomTheme} />
```

### 6.3 Per-Game Theming

```typescript
// In your game configuration
const gameConfig = {
  terminalTheme: {
    name: 'Space Station',
    background: '#0d1117',
    foreground: '#58a6ff',
    cursor: '#58a6ff',
    // ... more colors
  }
};

// Apply theme dynamically
function openGameTerminal() {
  openWindow({
    title: 'Ship Console',
    type: 'terminal',
    content: <TerminalApp theme={gameConfig.terminalTheme} />,
    // ...
  });
}
```

### 6.4 Styling Output Text

```typescript
// In your command execute function:

// Basic colors
session.writeLine('Success!', { color: 'var(--accent-green)' });
session.writeLine('Error!', { color: 'var(--accent-red)' });

// Bold text
session.writeLine('Important message', { bold: true });

// Italic text
session.writeLine('Note: This is a note', {
  italic: true,
  color: 'var(--text-secondary)'
});

// Underlined text
session.writeLine('Click here', { underline: true });

// Combination
session.writeLine('CRITICAL ERROR', {
  color: '#ff0000',
  bold: true,
  underline: true
});

// Custom background
session.writeLine(' HIGHLIGHTED ', {
  backgroundColor: '#ffff00',
  color: '#000000'
});

// Dim text (for secondary information)
session.writeLine('Optional details...', {
  dim: true
});
```

---

## 7. Advanced Features

### 7.1 Streaming Output

For long-running commands that produce gradual output:

```typescript
const scanCommand: Command = {
  name: 'scan',
  description: 'Scan network for devices',
  usage: 'scan',

  async execute(context) {
    const { session } = context;

    session.writeLine('Scanning network...');
    session.writeLine('');

    const devices = [
      '192.168.1.1 - Router',
      '192.168.1.10 - Desktop',
      '192.168.1.15 - Laptop',
      '192.168.1.20 - Phone',
      '192.168.1.25 - IoT Device',
    ];

    for (const device of devices) {
      // Simulate delay
      await new Promise(resolve => setTimeout(resolve, 500));

      session.writeLine(`Found: ${device}`, {
        color: 'var(--accent-cyan)'
      });
    }

    session.writeLine('');
    session.writeLine(`Scan complete. Found ${devices.length} devices.`);
  }
};
```

### 7.2 Progress Indicators

```typescript
const downloadCommand: Command = {
  name: 'download',
  description: 'Download a file from remote server',
  usage: 'download <url> <destination>',

  async execute(context) {
    const { session, args } = context;

    if (args.length < 2) {
      session.writeLine('Usage: download <url> <destination>');
      return;
    }

    const [url, dest] = args;

    session.writeLine(`Downloading ${url}...`);

    // Simulate download with progress bar
    for (let progress = 0; progress <= 100; progress += 10) {
      await new Promise(resolve => setTimeout(resolve, 200));

      const filled = Math.floor(progress / 5);
      const empty = 20 - filled;
      const bar = '█'.repeat(filled) + '░'.repeat(empty);

      // Update the same line
      session.updateLastLine(`Progress: [${bar}] ${progress}%`);
    }

    session.writeLine('');
    session.writeLine(`File saved to ${dest}`, {
      color: 'var(--accent-green)'
    });
  }
};
```

### 7.3 Interactive Prompts

```typescript
const configCommand: Command = {
  name: 'config',
  description: 'Configure system settings',
  usage: 'config',

  async execute(context) {
    const { session } = context;

    // Ask for username
    session.write('Enter username: ');
    const username = await session.readLine();

    // Ask for email
    session.write('Enter email: ');
    const email = await session.readLine();

    // Confirmation
    session.writeLine('');
    session.writeLine('Configuration:');
    session.writeLine(`  Username: ${username}`);
    session.writeLine(`  Email: ${email}`);
    session.writeLine('');

    session.write('Save configuration? (y/n): ');
    const confirm = await session.readLine();

    if (confirm.toLowerCase() === 'y') {
      // Save configuration
      gameState.config.username = username;
      gameState.config.email = email;

      session.writeLine('Configuration saved.', {
        color: 'var(--accent-green)'
      });
    } else {
      session.writeLine('Configuration cancelled.');
    }
  }
};
```

### 7.4 Command Aliases

```typescript
// Register command aliases
registry.registerAlias('ll', 'ls -la');
registry.registerAlias('cls', 'clear');
registry.registerAlias('..', 'cd ..');
registry.registerAlias('~', 'cd ~');

// Now users can type:
// $ ll        (executes: ls -la)
// $ cls       (executes: clear)
// $ ..        (executes: cd ..)
```

### 7.5 Environment Variables

```typescript
// Set environment variables
session.setEnv('USER', 'player');
session.setEnv('HOME', '/home/player');
session.setEnv('PATH', '/bin:/usr/bin');

// Use in commands
const envCommand: Command = {
  name: 'env',
  description: 'Display environment variables',
  usage: 'env',

  execute(context) {
    const { session } = context;
    const env = session.getEnv();

    env.forEach((value, key) => {
      session.writeLine(`${key}=${value}`);
    });
  }
};

// Variable expansion in echo
const echoCommand: Command = {
  name: 'echo',
  description: 'Print text',
  usage: 'echo <text>',

  execute(context) {
    const { session, args } = context;
    let text = args.join(' ');

    // Replace $VAR with environment variable
    text = text.replace(/\$(\w+)/g, (match, varName) => {
      return session.getEnv(varName) || match;
    });

    session.writeLine(text);
  }
};

// Usage:
// $ echo $USER
// player
```

---

## 8. Best Practices

### 8.1 Command Design

✅ **DO:**
- Provide clear error messages with usage information
- Use consistent flag naming (`-a`, `-l`, `-h`)
- Support `--help` flag for all commands
- Validate arguments before execution
- Use async/await for file system operations
- Provide tab completion for common arguments

❌ **DON'T:**
- Assume arguments are valid
- Block the UI with long operations
- Forget to handle errors
- Use inconsistent naming conventions

### 8.2 Application Design

✅ **DO:**
- Save state before unmounting
- Handle all key combinations
- Provide clear exit instructions
- Use consistent UI layout
- Render efficiently

❌ **DON'T:**
- Forget to return `false` when exiting
- Ignore resize events
- Render entire screen on every keystroke
- Assume fixed terminal dimensions

### 8.3 Performance

✅ **DO:**
- Use virtual scrolling for large outputs
- Batch multiple writes
- Clean up old output buffer entries
- Use `requestAnimationFrame` for animations

❌ **DON'T:**
- Write individual characters with separate calls
- Keep unlimited history
- Block the UI thread

### 8.4 User Experience

✅ **DO:**
- Provide helpful error messages
- Show progress for long operations
- Use colors meaningfully (red=error, green=success)
- Include keyboard shortcuts documentation
- Add command completion

❌ **DON'T:**
- Use too many colors (keep it readable)
- Ignore accessibility
- Provide cryptic error messages

---

## 9. API Reference

### 9.1 TerminalSession

```typescript
class TerminalSession {
  // Output methods
  write(text: string, style?: TextStyle): void;
  writeLine(text: string, style?: TextStyle): void;
  writeError(text: string): void;
  clearScreen(): void;
  updateLastLine(text: string): void;

  // Input methods
  readLine(): Promise<string>;
  waitForKey(): Promise<string>;

  // Directory methods
  getWorkingDirectory(): string;
  changeDirectory(path: string): Promise<void>;
  getPrompt(): string;
  setPrompt(prompt: string): void;

  // History methods
  addToHistory(command: string): void;
  getHistory(): string[];
  navigateHistory(direction: 'up' | 'down'): string | null;

  // Environment methods
  getEnv(key?: string): string | Map<string, string>;
  setEnv(key: string, value: string): void;
  deleteEnv(key: string): void;

  // Application methods
  launchApp(app: TerminalApplication): Promise<void>;

  // Completion methods
  complete(commandLine: string, cursorPosition: number): Promise<CompletionResult>;
}
```

### 9.2 CommandRegistry

```typescript
class CommandRegistry {
  register(command: Command): void;
  unregister(name: string): void;
  get(name: string): Command | undefined;
  getAll(): Command[];
  registerAlias(alias: string, command: string): void;
  execute(name: string, context: CommandContext): Promise<void>;
}
```

### 9.3 Command Interface

```typescript
interface Command {
  name: string;
  description: string;
  usage: string;
  options?: CommandOption[];
  execute: (context: CommandContext) => Promise<void> | void;
  complete?: (context: CompletionContext) => Promise<string[]> | string[];
}

interface CommandContext {
  session: TerminalSession;
  args: string[];
  options: Map<string, string | boolean>;
  rawInput: string;
  api: AppAPI;
}

interface CommandOption {
  flag: string;
  description: string;
  takesValue?: boolean;
}
```

### 9.4 TextStyle Interface

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
```

### 9.5 TerminalApplication Interface

```typescript
interface TerminalApplication {
  name: string;
  onMount(session: TerminalSession): Promise<void>;
  onUnmount(): Promise<void>;
  onKeyPress(key: string, modifiers: KeyModifiers): Promise<boolean>;
  onResize?(width: number, height: number): void;
  render(): string;
}

interface KeyModifiers {
  ctrl: boolean;
  alt: boolean;
  shift: boolean;
  meta: boolean;
}
```

---

## 10. Examples Repository

Complete working examples are available in:

```
frontend/src/terminal/examples/
├── commands/
│   ├── fortune.ts
│   ├── weather.ts
│   └── tasks.ts
├── apps/
│   ├── SimpleEditor.ts
│   ├── FileBrowser.ts
│   └── Calculator.ts
└── games/
    ├── WordGuess.ts
    ├── HackingGame.ts
    └── NumberGuess.ts
```

---

## Summary

The Terminal System provides a powerful, flexible foundation for building:
- Custom command-line tools
- Text-based applications
- Interactive mini-games
- Developer consoles

With a simple, well-documented API, game developers can easily extend the terminal to fit their specific needs while maintaining a consistent, professional user experience.

**Key Features:**
- 🎨 Fully themeable and styleable
- 🔧 Easy to extend with custom commands
- 🎮 Supports full-screen applications and games
- ⚡ High performance with virtual scrolling
- 🎯 Tab completion and command history
- 📝 Rich text formatting (colors, bold, italic)
- 🔌 Integrates with existing file system
- 📚 Well-documented with examples
