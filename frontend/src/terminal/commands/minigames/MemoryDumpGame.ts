/**
 * MemoryDump Game Logic
 *
 * A Fallout-style word-matching game where players must find the correct password
 * in a grid of characters and symbols.
 */

import { getRandomWords } from './wordlists';

export type Difficulty = 'easy' | 'medium' | 'hard';
export type GameStatus = 'playing' | 'won' | 'lost';
export type BracketType = '[]' | '()' | '{}' | '<>';

export interface GridCell {
  char: string;
  address: string;
  type: 'word' | 'garbage' | 'bracket';
  wordIndex?: number;
}

export interface WordPosition {
  word: string;
  isTarget: boolean;
  removed: boolean;
  startRow: number;
  startCol: number;
}

export interface DudRemover {
  type: BracketType;
  used: boolean;
  startRow: number;
  startCol: number;
  endCol: number;
}

export interface GuessAttempt {
  word: string;
  likeness: number;
}

export interface MemoryDumpState {
  targetWord: string;
  grid: GridCell[][];
  words: WordPosition[];
  dudRemovers: DudRemover[];
  attempts: GuessAttempt[];
  maxAttempts: number;
  gameStatus: GameStatus;
  difficulty: Difficulty;
}

interface DifficultyConfig {
  wordLength: number;
  wordCount: number;
  attempts: number;
  rows: number;
  cols: number;
  dudRemovers: number;
}

export class MemoryDumpGame {
  private state: MemoryDumpState;
  private config: DifficultyConfig;

  constructor(difficulty: Difficulty = 'medium') {
    this.config = this.getDifficultyConfig(difficulty);
    this.state = this.initializeGame(difficulty);
  }

  private getDifficultyConfig(difficulty: Difficulty): DifficultyConfig {
    const configs: Record<Difficulty, DifficultyConfig> = {
      easy: { wordLength: 4, wordCount: 6, attempts: 5, rows: 12, cols: 12, dudRemovers: 3 },
      medium: { wordLength: 5, wordCount: 8, attempts: 4, rows: 16, cols: 12, dudRemovers: 2 },
      hard: { wordLength: 6, wordCount: 10, attempts: 3, rows: 16, cols: 12, dudRemovers: 1 },
    };
    return configs[difficulty];
  }

  private initializeGame(difficulty: Difficulty): MemoryDumpState {
    const { target, decoys } = getRandomWords(
      this.config.wordLength,
      this.config.wordCount
    );

    const allWords = [target, ...decoys];
    const grid = this.generateGrid();
    const words = this.placeWords(grid, allWords);
    const dudRemovers = this.placeDudRemovers(grid);

    return {
      targetWord: target,
      grid,
      words,
      dudRemovers,
      attempts: [],
      maxAttempts: this.config.attempts,
      gameStatus: 'playing',
      difficulty,
    };
  }

  private generateGrid(): GridCell[][] {
    const grid: GridCell[][] = [];
    const totalCols = this.config.cols * 2; // Two columns side-by-side

    // Initialize with garbage
    for (let r = 0; r < this.config.rows; r++) {
      grid[r] = [];
      for (let c = 0; c < totalCols; c++) {
        grid[r][c] = {
          char: this.getRandomGarbage(),
          address: this.getMemoryAddress(r, c),
          type: 'garbage',
        };
      }
    }

    return grid;
  }

  private getRandomGarbage(): string {
    const garbage = '!@#$%^&*()_+-=[]{}|;:,.<>?/~`';
    return garbage[Math.floor(Math.random() * garbage.length)];
  }

  private getMemoryAddress(row: number, col: number): string {
    const base = 0x0A00;
    const offset = row * 16 + (col < this.config.cols ? 0 : 8);
    return `0x${(base + offset).toString(16).toUpperCase().padStart(4, '0')}`;
  }

  private placeWords(grid: GridCell[][], words: string[]): WordPosition[] {
    const positions: WordPosition[] = [];
    const rows = grid.length;
    const cols = grid[0].length;

    for (let i = 0; i < words.length; i++) {
      const word = words[i];
      let placed = false;
      let attempts = 0;

      while (!placed && attempts < 200) {
        const row = Math.floor(Math.random() * rows);
        const col = Math.floor(Math.random() * (cols - word.length + 1));

        // Check if space is available
        if (this.canPlaceWord(grid, word, row, col)) {
          this.placeWord(grid, word, row, col, i);
          positions.push({
            word,
            isTarget: i === 0, // First word is target
            removed: false,
            startRow: row,
            startCol: col,
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

  private canPlaceWord(
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

  private placeWord(
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

  private placeDudRemovers(grid: GridCell[][]): DudRemover[] {
    const brackets: BracketType[] = ['[]', '()', '{}', '<>'];
    const removers: DudRemover[] = [];

    for (let i = 0; i < this.config.dudRemovers; i++) {
      const bracketType = brackets[i % brackets.length];
      const opening = bracketType[0];
      const closing = bracketType[1];

      let placed = false;
      let attempts = 0;

      while (!placed && attempts < 100) {
        const row = Math.floor(Math.random() * grid.length);
        const startCol = Math.floor(Math.random() * (grid[0].length - 4));
        const length = 2 + Math.floor(Math.random() * 3); // 2-4 chars between
        const endCol = startCol + length + 1;

        // Check if space is available (only garbage)
        let available = true;
        for (let c = startCol; c <= endCol && c < grid[0].length; c++) {
          if (grid[row][c].type !== 'garbage') {
            available = false;
            break;
          }
        }

        if (available && endCol < grid[0].length) {
          grid[row][startCol].char = opening;
          grid[row][startCol].type = 'bracket';
          grid[row][endCol].char = closing;
          grid[row][endCol].type = 'bracket';

          removers.push({
            type: bracketType,
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

  /**
   * Calculate likeness between two words
   * Returns the number of characters that match in the same position
   */
  private calculateLikeness(guess: string, target: string): number {
    let likeness = 0;
    for (let i = 0; i < guess.length; i++) {
      if (guess[i] === target[i]) {
        likeness++;
      }
    }
    return likeness;
  }

  /**
   * Select a word from the grid
   */
  public selectWord(word: string): {
    correct: boolean;
    likeness?: number;
    gameOver: boolean;
    alreadyRemoved?: boolean;
  } {
    if (this.state.gameStatus !== 'playing') {
      return { correct: false, gameOver: true };
    }

    const normalizedWord = word.toUpperCase().trim();

    // Find the word in our word list
    const wordPos = this.state.words.find(w => w.word === normalizedWord);

    if (!wordPos) {
      return { correct: false, likeness: -1, gameOver: false };
    }

    if (wordPos.removed) {
      return { correct: false, alreadyRemoved: true, gameOver: false };
    }

    // Check if it's the target
    if (wordPos.isTarget) {
      this.state.gameStatus = 'won';
      return { correct: true, gameOver: true };
    }

    // Calculate likeness
    const likeness = this.calculateLikeness(normalizedWord, this.state.targetWord);

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

  /**
   * Activate a dud remover at specific grid position
   */
  public activateDudRemover(row: number, col: number): {
    activated: boolean;
    effect: 'remove_dud' | 'restore_attempt' | null;
    removedWord?: string;
  } {
    // Find matching dud remover
    const remover = this.state.dudRemovers.find(
      dr =>
        dr.startRow === row &&
        (dr.startCol === col || dr.endCol === col) &&
        !dr.used
    );

    if (!remover) {
      return { activated: false, effect: null };
    }

    remover.used = true;

    // Randomly choose effect (50/50)
    const effect: 'remove_dud' | 'restore_attempt' =
      Math.random() < 0.5 ? 'remove_dud' : 'restore_attempt';

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

        return { activated: true, effect, removedWord: toRemove.word };
      }
    } else {
      // Restore one attempt
      if (this.state.attempts.length > 0) {
        this.state.attempts.pop();
      }
    }

    return { activated: true, effect };
  }

  /**
   * Get all available (non-removed) words
   */
  public getAvailableWords(): string[] {
    return this.state.words
      .filter(w => !w.removed)
      .map(w => w.word);
  }

  /**
   * Get remaining attempts
   */
  public getRemainingAttempts(): number {
    return this.state.maxAttempts - this.state.attempts.length;
  }

  /**
   * Get current game state (immutable)
   */
  public getState(): Readonly<MemoryDumpState> {
    return {
      ...this.state,
      grid: this.state.grid.map(row => [...row]),
      words: [...this.state.words],
      dudRemovers: [...this.state.dudRemovers],
      attempts: [...this.state.attempts],
    };
  }
}
