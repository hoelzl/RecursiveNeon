/**
 * CodeBreaker Game Logic
 *
 * A Bulls & Cows / Wordle variant where players guess hexadecimal codes.
 * Pure TypeScript class with no UI dependencies for easy testing.
 */

export type Difficulty = 'easy' | 'medium' | 'hard';
export type FeedbackStatus = 'exact' | 'partial' | 'miss';
export type GameStatus = 'playing' | 'won' | 'lost';

export interface FeedbackChar {
  char: string;
  status: FeedbackStatus;
}

export interface Guess {
  input: string;
  feedback: FeedbackChar[];
}

export interface CodeBreakerState {
  code: string;
  guesses: Guess[];
  maxAttempts: number;
  gameStatus: GameStatus;
  difficulty: Difficulty;
}

interface DifficultyConfig {
  length: number;
  attempts: number;
  charset: string;
}

export class CodeBreakerGame {
  private state: CodeBreakerState;
  private config: DifficultyConfig;

  constructor(difficulty: Difficulty = 'medium') {
    this.config = this.getDifficultyConfig(difficulty);
    this.state = this.initializeGame(difficulty);
  }

  private getDifficultyConfig(difficulty: Difficulty): DifficultyConfig {
    const configs: Record<Difficulty, DifficultyConfig> = {
      easy: { length: 4, attempts: 12, charset: '0123456789' },
      medium: { length: 4, attempts: 10, charset: '0123456789ABCDEF' },
      hard: { length: 6, attempts: 8, charset: '0123456789ABCDEF' },
    };
    return configs[difficulty];
  }

  private initializeGame(difficulty: Difficulty): CodeBreakerState {
    return {
      code: this.generateCode(this.config.length, this.config.charset),
      guesses: [],
      maxAttempts: this.config.attempts,
      gameStatus: 'playing',
      difficulty,
    };
  }

  private generateCode(length: number, charset: string): string {
    let code = '';
    for (let i = 0; i < length; i++) {
      code += charset[Math.floor(Math.random() * charset.length)];
    }
    return code;
  }

  /**
   * Validate a guess input
   */
  public validateGuess(input: string): { valid: boolean; error?: string } {
    const normalized = input.toUpperCase().trim();

    if (normalized.length !== this.config.length) {
      return {
        valid: false,
        error: `Code must be exactly ${this.config.length} characters`,
      };
    }

    const validPattern = new RegExp(`^[${this.config.charset}]+$`);
    if (!validPattern.test(normalized)) {
      return {
        valid: false,
        error: `Code must contain only valid characters (${this.config.charset})`,
      };
    }

    return { valid: true };
  }

  /**
   * Make a guess and get feedback
   */
  public makeGuess(guess: string): Guess {
    if (this.state.gameStatus !== 'playing') {
      throw new Error('Game is not in playing state');
    }

    const normalizedGuess = guess.toUpperCase().trim();
    const feedback = this.checkGuess(normalizedGuess, this.state.code);
    const guessObj: Guess = { input: normalizedGuess, feedback };

    this.state.guesses.push(guessObj);

    // Check win condition
    if (feedback.every(f => f.status === 'exact')) {
      this.state.gameStatus = 'won';
    }
    // Check lose condition
    else if (this.state.guesses.length >= this.state.maxAttempts) {
      this.state.gameStatus = 'lost';
    }

    return guessObj;
  }

  /**
   * Check a guess against the code and return feedback
   *
   * Algorithm:
   * 1. First pass: Find exact matches (correct position)
   * 2. Second pass: Find partial matches (wrong position)
   * 3. Remaining are misses
   */
  private checkGuess(guess: string, code: string): FeedbackChar[] {
    const feedback: FeedbackChar[] = new Array(guess.length);
    const codeChars = code.split('');
    const guessChars = guess.split('');

    // Track which characters have been matched
    const codeUsed = new Array(code.length).fill(false);
    const guessUsed = new Array(guess.length).fill(false);

    // First pass: Find exact matches
    for (let i = 0; i < guess.length; i++) {
      if (guessChars[i] === codeChars[i]) {
        feedback[i] = { char: guessChars[i], status: 'exact' };
        codeUsed[i] = true;
        guessUsed[i] = true;
      }
    }

    // Second pass: Find partial matches
    for (let i = 0; i < guess.length; i++) {
      if (guessUsed[i]) continue; // Skip exact matches

      let found = false;
      for (let j = 0; j < code.length; j++) {
        if (!codeUsed[j] && guessChars[i] === codeChars[j]) {
          feedback[i] = { char: guessChars[i], status: 'partial' };
          codeUsed[j] = true;
          found = true;
          break;
        }
      }

      if (!found) {
        feedback[i] = { char: guessChars[i], status: 'miss' };
      }
    }

    return feedback;
  }

  /**
   * Get the current game state (immutable)
   */
  public getState(): Readonly<CodeBreakerState> {
    return {
      ...this.state,
      guesses: [...this.state.guesses],
    };
  }

  /**
   * Get the code length for this difficulty
   */
  public getCodeLength(): number {
    return this.config.length;
  }

  /**
   * Get remaining attempts
   */
  public getRemainingAttempts(): number {
    return this.state.maxAttempts - this.state.guesses.length;
  }
}
