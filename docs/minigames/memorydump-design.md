# MemoryDump - Design Document

> **Game Type**: Terminal
> **Implementation**: TypeScript/React

---

## Architecture

### Component Structure

```
MemoryDumpGame (Core Logic)
  ├── generateGrid()
  ├── placeWords()
  ├── findDudRemovers()
  ├── calculateLikeness()
  ├── selectWord()
  └── getGameState()

MemoryDumpCommand (Terminal Integration)
  └── Uses MemoryDumpGame
```

## Game State

```typescript
interface MemoryDumpState {
  targetWord: string;
  grid: GridCell[][];
  words: WordPosition[];
  dudRemovers: DudRemover[];
  attempts: GuessAttempt[];
  maxAttempts: number;
  gameStatus: 'playing' | 'won' | 'lost';
  difficulty: 'easy' | 'medium' | 'hard';
}

interface GridCell {
  char: string;
  address: string;  // Memory address (hex)
  type: 'word' | 'garbage' | 'bracket';
  wordIndex?: number; // If part of a word, which word?
}

interface WordPosition {
  word: string;
  isTarget: boolean;
  removed: boolean; // If dud remover used
  startRow: number;
  startCol: number;
  cells: { row: number; col: number }[];
}

interface DudRemover {
  type: '[]' | '()' | '{}' | '<>';
  used: boolean;
  startRow: number;
  startCol: number;
  endCol: number;
}

interface GuessAttempt {
  word: string;
  likeness: number;
}
```

## Core Algorithms

### Word List Selection

```typescript
const WORD_LISTS = {
  4: ['BYTE', 'DATA', 'CODE', 'PORT', 'CORE', 'LOOP', 'DISK', 'LINK'],
  5: ['CYBER', 'PROXY', 'VIRUS', 'PROBE', 'TRACE', 'FRAME', 'PIXEL', 'LOGIC'],
  6: ['SYSTEM', 'PACKET', 'ROUTER', 'HACKER', 'KERNEL', 'DAEMON', 'VECTOR'],
  7: ['PROGRAM', 'NETWORK', 'DIGITAL', 'PROCESS', 'GATEWAY', 'ENCRYPT'],
  8: ['TERMINAL', 'PROTOCOL', 'DATABASE', 'PASSWORD', 'OVERFLOW'],
};

function selectWords(
  difficulty: string,
  wordCount: number
): { target: string; decoys: string[] } {
  const config = getDifficultyConfig(difficulty);
  const wordList = WORD_LISTS[config.wordLength];

  // Shuffle and select
  const shuffled = [...wordList].sort(() => Math.random() - 0.5);
  const target = shuffled[0];
  const decoys = shuffled.slice(1, wordCount);

  return { target, decoys };
}
```

### Grid Generation

```typescript
function generateGrid(
  words: string[],
  rows: number = 16,
  cols: number = 12
): GridCell[][] {
  const grid: GridCell[][] = [];
  const totalCols = cols * 2; // Two columns side-by-side

  // Initialize with garbage
  for (let r = 0; r < rows; r++) {
    grid[r] = [];
    for (let c = 0; c < totalCols; c++) {
      grid[r][c] = {
        char: getRandomGarbage(),
        address: getMemoryAddress(r, c),
        type: 'garbage',
      };
    }
  }

  return grid;
}

function getRandomGarbage(): string {
  const garbage = '!@#$%^&*()_+-=[]{}|;:,.<>?/~`';
  return garbage[Math.floor(Math.random() * garbage.length)];
}

function getMemoryAddress(row: number, col: number): string {
  const base = 0x0A00;
  const offset = row * 16 + (col < 12 ? 0 : 8);
  return `0x${(base + offset).toString(16).toUpperCase().padStart(4, '0')}`;
}
```

### Word Placement

```typescript
function placeWords(
  grid: GridCell[][],
  words: string[]
): WordPosition[] {
  const positions: WordPosition[] = [];
  const rows = grid.length;
  const cols = grid[0].length;

  for (let i = 0; i < words.length; i++) {
    const word = words[i];
    let placed = false;
    let attempts = 0;

    while (!placed && attempts < 100) {
      const row = Math.floor(Math.random() * rows);
      const col = Math.floor(Math.random() * (cols - word.length + 1));

      // Check if space is available
      if (canPlaceWord(grid, word, row, col)) {
        placeWord(grid, word, row, col, i);
        positions.push({
          word,
          isTarget: i === 0, // First word is target
          removed: false,
          startRow: row,
          startCol: col,
          cells: getCellPositions(row, col, word.length),
        });
        placed = true;
      }

      attempts++;
    }

    if (!placed) {
      console.warn(`Failed to place word: ${word}`);
    }
  }

  return positions;
}

function canPlaceWord(
  grid: GridCell[][],
  word: string,
  row: number,
  col: number
): boolean {
  // Check if all cells are garbage (not already part of a word)
  for (let i = 0; i < word.length; i++) {
    if (grid[row][col + i].type !== 'garbage') {
      return false;
    }
  }
  return true;
}

function placeWord(
  grid: GridCell[][],
  word: string,
  row: number,
  col: number,
  wordIndex: number
): void {
  for (let i = 0; i < word.length; i++) {
    grid[row][col + i] = {
      char: word[i],
      address: grid[row][col + i].address,
      type: 'word',
      wordIndex,
    };
  }
}
```

### Dud Remover Placement

```typescript
function placeDudRemovers(
  grid: GridCell[][],
  count: number
): DudRemover[] {
  const brackets = ['[]', '()', '{}', '<>'];
  const removers: DudRemover[] = [];

  for (let i = 0; i < count; i++) {
    const bracketType = brackets[i % brackets.length];
    const opening = bracketType[0];
    const closing = bracketType[1];

    let placed = false;
    let attempts = 0;

    while (!placed && attempts < 100) {
      const row = Math.floor(Math.random() * grid.length);
      const startCol = Math.floor(Math.random() * (grid[0].length - 4));
      const length = 2 + Math.floor(Math.random() * 4); // 2-5 chars between
      const endCol = startCol + length + 1;

      // Check if space is available (only garbage)
      let available = true;
      for (let c = startCol; c <= endCol; c++) {
        if (grid[row][c].type !== 'garbage') {
          available = false;
          break;
        }
      }

      if (available) {
        grid[row][startCol].char = opening;
        grid[row][startCol].type = 'bracket';
        grid[row][endCol].char = closing;
        grid[row][endCol].type = 'bracket';

        removers.push({
          type: bracketType as any,
          used: false,
          startRow: row,
          startCol,
          endCol,
        });

        placed = true;
      }

      attempts++;
    }
  }

  return removers;
}
```

### Likeness Calculation

```typescript
function calculateLikeness(guess: string, target: string): number {
  let likeness = 0;

  for (let i = 0; i < guess.length; i++) {
    if (guess[i] === target[i]) {
      likeness++;
    }
  }

  return likeness;
}
```

### Word Selection Logic

```typescript
function selectWord(word: string): {
  correct: boolean;
  likeness?: number;
  gameOver: boolean;
} {
  const normalizedWord = word.toUpperCase();

  // Find the word in our word list
  const wordPos = this.state.words.find(w => w.word === normalizedWord);

  if (!wordPos) {
    return { correct: false, likeness: 0, gameOver: false };
  }

  if (wordPos.removed) {
    return { correct: false, likeness: -1, gameOver: false }; // Already removed
  }

  if (wordPos.isTarget) {
    this.state.gameStatus = 'won';
    return { correct: true, gameOver: true };
  }

  // Calculate likeness
  const likeness = calculateLikeness(normalizedWord, this.state.targetWord);

  this.state.attempts.push({
    word: normalizedWord,
    likeness,
  });

  // Check if out of attempts
  if (this.state.attempts.length >= this.state.maxAttempts) {
    this.state.gameStatus = 'lost';
    return { correct: false, likeness, gameOver: true };
  }

  return { correct: false, likeness, gameOver: false };
}
```

### Dud Remover Activation

```typescript
function activateDudRemover(row: number, col: number): {
  activated: boolean;
  effect: 'remove_dud' | 'restore_attempt' | null;
} {
  // Find matching dud remover
  const remover = this.state.dudRemovers.find(
    dr => dr.startRow === row &&
          (dr.startCol === col || dr.endCol === col) &&
          !dr.used
  );

  if (!remover) {
    return { activated: false, effect: null };
  }

  remover.used = true;

  // Randomly choose effect (50/50)
  const effect = Math.random() < 0.5 ? 'remove_dud' : 'restore_attempt';

  if (effect === 'remove_dud') {
    // Remove a random non-target word
    const availableWords = this.state.words.filter(
      w => !w.isTarget && !w.removed
    );

    if (availableWords.length > 0) {
      const toRemove = availableWords[
        Math.floor(Math.random() * availableWords.length)
      ];
      toRemove.removed = true;
    }
  } else {
    // Restore one attempt
    if (this.state.attempts.length > 0) {
      this.state.attempts.pop();
    }
  }

  return { activated: true, effect };
}
```

## Display Rendering

### Grid Display

```typescript
function displayGrid(session: TerminalSession, grid: GridCell[][]): void {
  const colsPerSide = grid[0].length / 2;

  for (let r = 0; r < grid.length; r++) {
    // Left column
    session.write(grid[r][0].address + '  ');

    for (let c = 0; c < colsPerSide; c++) {
      const cell = grid[r][c];
      const color = getCellColor(cell);
      session.write(cell.char, color);
    }

    session.write('  '); // Space between columns

    // Right column
    session.write(grid[r][colsPerSide].address + '  ');

    for (let c = colsPerSide; c < grid[0].length; c++) {
      const cell = grid[r][c];
      const color = getCellColor(cell);
      session.write(cell.char, color);
    }

    session.writeLine('');
  }
}

function getCellColor(cell: GridCell): string {
  if (cell.type === 'word') return 'green';
  if (cell.type === 'bracket') return 'yellow';
  return 'gray';
}
```

### Status Display

```typescript
function displayStatus(session: TerminalSession, state: MemoryDumpState): void {
  session.writeLine('');
  session.writeLine('ROBCO INDUSTRIES (TM) TERMLINK PROTOCOL');
  session.writeLine('ENTER PASSWORD NOW');
  session.writeLine('');

  const remaining = state.maxAttempts - state.attempts.length;
  const blocks = '█'.repeat(remaining);
  session.writeLine(`Attempts Remaining: ${blocks}`, 'cyan');
  session.writeLine('');

  if (state.attempts.length > 0) {
    session.writeLine('Previous Attempts:');
    state.attempts.forEach(attempt => {
      session.writeLine(
        `> ${attempt.word.padEnd(10)} Likeness: ${attempt.likeness}/${state.targetWord.length}`
      );
    });
    session.writeLine('');
  }
}
```

## Class Structure

```typescript
export class MemoryDumpGame {
  private state: MemoryDumpState;

  constructor(difficulty: 'easy' | 'medium' | 'hard' = 'medium') {
    this.state = this.initializeGame(difficulty);
  }

  private initializeGame(difficulty: string): MemoryDumpState {
    const config = this.getDifficultyConfig(difficulty);
    const { target, decoys } = this.selectWords(config);
    const allWords = [target, ...decoys];

    const grid = this.generateGrid(config.rows, config.cols);
    const words = this.placeWords(grid, allWords);
    const dudRemovers = this.placeDudRemovers(grid, config.dudRemovers);

    return {
      targetWord: target,
      grid,
      words,
      dudRemovers,
      attempts: [],
      maxAttempts: config.attempts,
      gameStatus: 'playing',
      difficulty: difficulty as any,
    };
  }

  public selectWord(word: string): SelectionResult { /* ... */ }
  public activateDudRemover(row: number, col: number): DudRemoverResult { /* ... */ }
  public getState(): Readonly<MemoryDumpState> { return { ...this.state }; }
  public getAvailableWords(): string[] {
    return this.state.words
      .filter(w => !w.removed)
      .map(w => w.word);
  }

  // Private methods: generateGrid, placeWords, etc.
}
```

## Testing Strategy

```typescript
describe('MemoryDumpGame', () => {
  describe('Initialization', () => {
    it('generates grid of correct size', () => {
      const game = new MemoryDumpGame('medium');
      const state = game.getState();
      expect(state.grid.length).toBe(16);
      expect(state.grid[0].length).toBe(24); // 2 columns of 12
    });

    it('places target word in grid', () => {
      const game = new MemoryDumpGame('medium');
      const state = game.getState();
      expect(state.words.find(w => w.isTarget)).toBeDefined();
    });

    it('all words have same length', () => {
      const game = new MemoryDumpGame('medium');
      const state = game.getState();
      const lengths = state.words.map(w => w.word.length);
      expect(new Set(lengths).size).toBe(1);
    });
  });

  describe('Likeness Calculation', () => {
    it('calculates exact match as full likeness', () => {
      const game = new MemoryDumpGame('medium');
      game['state'].targetWord = 'SYSTEM';

      const result = game.selectWord('SYSTEM');
      expect(result.correct).toBe(true);
    });

    it('calculates partial likeness correctly', () => {
      const game = new MemoryDumpGame('medium');
      game['state'].targetWord = 'SYSTEM';

      // Set up decoy word
      game['state'].words.push({
        word: 'SOCKET',
        isTarget: false,
        removed: false,
        startRow: 0,
        startCol: 0,
        cells: [],
      });

      const result = game.selectWord('SOCKET');
      expect(result.correct).toBe(false);
      expect(result.likeness).toBe(1); // Only 'S' matches in position
    });

    it('calculates zero likeness correctly', () => {
      const game = new MemoryDumpGame('medium');
      game['state'].targetWord = 'SYSTEM';

      game['state'].words.push({
        word: 'HACKER',
        isTarget: false,
        removed: false,
        startRow: 0,
        startCol: 0,
        cells: [],
      });

      const result = game.selectWord('HACKER');
      expect(result.likeness).toBe(0);
    });
  });

  describe('Game State', () => {
    it('wins when correct word selected', () => {
      const game = new MemoryDumpGame('medium');
      const target = game.getState().targetWord;

      game.selectWord(target);
      expect(game.getState().gameStatus).toBe('won');
    });

    it('loses after max attempts', () => {
      const game = new MemoryDumpGame('medium');
      const words = game.getAvailableWords().filter(
        w => w !== game.getState().targetWord
      );

      for (let i = 0; i < 4; i++) {
        game.selectWord(words[i % words.length]);
      }

      expect(game.getState().gameStatus).toBe('lost');
    });
  });

  describe('Dud Removers', () => {
    it('removes a word when activated', () => {
      const game = new MemoryDumpGame('medium');
      const initialCount = game.getAvailableWords().length;

      // Find a dud remover
      const remover = game.getState().dudRemovers[0];
      if (remover) {
        const result = game.activateDudRemover(
          remover.startRow,
          remover.startCol
        );

        if (result.effect === 'remove_dud') {
          expect(game.getAvailableWords().length).toBeLessThan(initialCount);
        }
      }
    });

    it('cannot be used twice', () => {
      const game = new MemoryDumpGame('medium');
      const remover = game.getState().dudRemovers[0];

      if (remover) {
        game.activateDudRemover(remover.startRow, remover.startCol);
        const result = game.activateDudRemover(remover.startRow, remover.startCol);

        expect(result.activated).toBe(false);
      }
    });
  });
});
```

## File Structure

```
frontend/src/
├── terminal/
│   └── commands/
│       ├── minigames/
│       │   ├── MemoryDumpGame.ts        # Core game logic
│       │   ├── MemoryDumpGame.test.ts   # Unit tests
│       │   ├── memorydump-command.ts    # Terminal integration
│       │   └── wordlists.ts             # Word lists by length
```

## Future Enhancements

- [ ] Word highlighting on hover (if terminal supports mouse)
- [ ] Difficulty selection during gameplay
- [ ] Custom word lists
- [ ] Statistics tracking
- [ ] Sound effects
- [ ] Animation for dud removal

---

## Summary

MemoryDump provides a challenging word-deduction puzzle that:
- Tests pattern recognition and logical deduction
- Creates authentic "hacking" atmosphere
- Offers strategic depth with dud removers
- Remains replayable with randomized grids
- Maintains clean architecture for testing and extension
