# CodeBreaker - Design Document

> **Game Type**: Terminal
> **Implementation**: TypeScript/React

---

## Architecture

### Component Structure

```
CodeBreakerGame (Game Logic - Testable)
  ├── generateCode()
  ├── validateGuess()
  ├── checkGuess()
  └── getGameState()

CodeBreakerCommand (Terminal Integration)
  └── Uses CodeBreakerGame for logic
```

### Separation of Concerns

- **Game Logic** (`CodeBreakerGame`): Pure TypeScript class, no UI dependencies
- **Terminal Integration** (`CodeBreakerCommand`): Handles I/O, uses game logic
- **Utilities**: Color formatting, validation helpers

## Game State

```typescript
interface CodeBreakerState {
  code: string;              // The secret code
  guesses: Guess[];          // History of guesses
  maxAttempts: number;       // Default: 10
  gameStatus: 'playing' | 'won' | 'lost';
  difficulty: 'easy' | 'medium' | 'hard';
}

interface Guess {
  input: string;
  feedback: FeedbackChar[];
}

interface FeedbackChar {
  char: string;
  status: 'exact' | 'partial' | 'miss';
}
```

## Core Algorithms

### Code Generation

```typescript
generateCode(length: number = 4): string {
  const chars = '0123456789ABCDEF';
  let code = '';
  for (let i = 0; i < length; i++) {
    code += chars[Math.floor(Math.random() * chars.length)];
  }
  return code;
}
```

### Guess Checking Algorithm

```typescript
checkGuess(guess: string, code: string): FeedbackChar[] {
  const feedback: FeedbackChar[] = [];
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
```

### Input Validation

```typescript
validateGuess(input: string, length: number = 4): {
  valid: boolean;
  error?: string;
} {
  const normalized = input.toUpperCase().trim();

  if (normalized.length !== length) {
    return {
      valid: false,
      error: `Code must be exactly ${length} characters`
    };
  }

  const hexPattern = /^[0-9A-F]+$/;
  if (!hexPattern.test(normalized)) {
    return {
      valid: false,
      error: 'Code must contain only hex digits (0-9, A-F)'
    };
  }

  return { valid: true };
}
```

## Terminal Integration

### Command Structure

```typescript
import type { Command, CommandContext } from '../core/CommandRegistry';
import { CodeBreakerGame } from './CodeBreakerGame';

export const codebreakerCommand: Command = {
  name: 'codebreaker',
  description: 'Play the CodeBreaker hacking game',
  usage: 'codebreaker [--difficulty easy|medium|hard]',

  async execute(context: CommandContext): Promise<number> {
    const { session, args } = context;

    // Parse difficulty
    const difficulty = parseDifficulty(args);

    // Create game instance
    const game = new CodeBreakerGame(difficulty);

    // Display welcome
    displayWelcome(session, game);

    // Game loop
    while (game.getState().gameStatus === 'playing') {
      const guess = await session.readLine('Enter your guess: ');

      const validation = game.validateGuess(guess);
      if (!validation.valid) {
        session.writeLine(`Error: ${validation.error}`, 'error');
        continue;
      }

      const result = game.makeGuess(guess.toUpperCase());
      displayGuessResult(session, result, game.getState());

      if (game.getState().gameStatus !== 'playing') {
        displayGameEnd(session, game.getState());
        break;
      }
    }

    return 0;
  }
};
```

### Display Utilities

```typescript
function displayWelcome(session: TerminalSession, game: CodeBreakerGame) {
  const state = game.getState();
  session.writeLine('╔══════════════════════════════════════╗');
  session.writeLine('║       CODEBREAKER v1.0              ║');
  session.writeLine('║   Crack the hex code                ║');
  session.writeLine('╚══════════════════════════════════════╝');
  session.writeLine('');
  session.writeLine(`Difficulty: ${state.difficulty.toUpperCase()}`);
  session.writeLine(`Code length: ${state.code.length} characters`);
  session.writeLine(`Attempts: ${state.maxAttempts}`);
  session.writeLine('');
  session.writeLine('Feedback guide:');
  session.writeLine('  ✓ (Green)  = Correct position');
  session.writeLine('  ⚬ (Yellow) = Wrong position');
  session.writeLine('  ✗ (Gray)   = Not in code');
  session.writeLine('');
}

function displayGuessResult(
  session: TerminalSession,
  guess: Guess,
  state: CodeBreakerState
) {
  const remainingAttempts = state.maxAttempts - state.guesses.length;

  session.writeLine('');
  session.write(`Guess ${state.guesses.length}: `);

  // Display feedback with colors
  guess.feedback.forEach((fb) => {
    const color = fb.status === 'exact' ? 'green' :
                  fb.status === 'partial' ? 'yellow' : 'gray';
    const symbol = fb.status === 'exact' ? '✓' :
                   fb.status === 'partial' ? '⚬' : '✗';

    session.write(`[${fb.char}${symbol}]`, color);
  });

  session.writeLine('');

  const exactCount = guess.feedback.filter(f => f.status === 'exact').length;
  const partialCount = guess.feedback.filter(f => f.status === 'partial').length;

  session.writeLine(
    `  ${exactCount} exact, ${partialCount} partial`
  );
  session.writeLine(`Attempts remaining: ${remainingAttempts}`);
  session.writeLine('');
}

function displayGameEnd(session: TerminalSession, state: CodeBreakerState) {
  session.writeLine('');

  if (state.gameStatus === 'won') {
    session.writeLine('🎉 ACCESS GRANTED 🎉', 'success');
    session.writeLine(
      `Code cracked in ${state.guesses.length} attempts!`
    );
  } else {
    session.writeLine('❌ ACCESS DENIED ❌', 'error');
    session.writeLine('System locked.');
  }

  session.writeLine(`The code was: ${state.code}`);
  session.writeLine('');
}
```

## Class Structure

```typescript
export class CodeBreakerGame {
  private state: CodeBreakerState;

  constructor(difficulty: 'easy' | 'medium' | 'hard' = 'medium') {
    this.state = this.initializeGame(difficulty);
  }

  private initializeGame(difficulty: string): CodeBreakerState {
    const config = this.getDifficultyConfig(difficulty);

    return {
      code: this.generateCode(config.length),
      guesses: [],
      maxAttempts: config.attempts,
      gameStatus: 'playing',
      difficulty: difficulty as any,
    };
  }

  private getDifficultyConfig(difficulty: string) {
    const configs = {
      easy: { length: 4, attempts: 12, charset: '0123456789' },
      medium: { length: 4, attempts: 10, charset: '0123456789ABCDEF' },
      hard: { length: 6, attempts: 8, charset: '0123456789ABCDEF' },
    };
    return configs[difficulty] || configs.medium;
  }

  public makeGuess(guess: string): Guess {
    const feedback = this.checkGuess(guess, this.state.code);
    const guessObj = { input: guess, feedback };

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

  public getState(): Readonly<CodeBreakerState> {
    return { ...this.state };
  }

  public validateGuess(input: string): { valid: boolean; error?: string } {
    // Implementation as shown above
  }

  private generateCode(length: number): string {
    // Implementation as shown above
  }

  private checkGuess(guess: string, code: string): FeedbackChar[] {
    // Implementation as shown above
  }
}
```

## Testing Strategy

### Unit Tests

```typescript
describe('CodeBreakerGame', () => {
  describe('Code Generation', () => {
    it('generates code of correct length', () => {
      const game = new CodeBreakerGame('medium');
      expect(game.getState().code).toHaveLength(4);
    });

    it('generates code with valid hex characters', () => {
      const game = new CodeBreakerGame('medium');
      expect(game.getState().code).toMatch(/^[0-9A-F]+$/);
    });
  });

  describe('Guess Checking', () => {
    it('identifies exact matches correctly', () => {
      const game = new CodeBreakerGame('medium');
      // Use reflection or test double to set known code
      game['state'].code = 'CAFE';

      const result = game.makeGuess('CAFE');
      expect(result.feedback).toEqual([
        { char: 'C', status: 'exact' },
        { char: 'A', status: 'exact' },
        { char: 'F', status: 'exact' },
        { char: 'E', status: 'exact' },
      ]);
      expect(game.getState().gameStatus).toBe('won');
    });

    it('identifies partial matches correctly', () => {
      const game = new CodeBreakerGame('medium');
      game['state'].code = 'CAFE';

      const result = game.makeGuess('EFAC');
      expect(result.feedback.filter(f => f.status === 'partial')).toHaveLength(4);
    });

    it('handles repeated characters correctly', () => {
      const game = new CodeBreakerGame('medium');
      game['state'].code = 'AAAA';

      const result = game.makeGuess('AAAB');
      const exactCount = result.feedback.filter(f => f.status === 'exact').length;
      const missCount = result.feedback.filter(f => f.status === 'miss').length;

      expect(exactCount).toBe(3);
      expect(missCount).toBe(1);
    });
  });

  describe('Game State', () => {
    it('starts with playing status', () => {
      const game = new CodeBreakerGame('medium');
      expect(game.getState().gameStatus).toBe('playing');
    });

    it('sets won status when code is guessed', () => {
      const game = new CodeBreakerGame('medium');
      game['state'].code = 'DEAD';
      game.makeGuess('DEAD');
      expect(game.getState().gameStatus).toBe('won');
    });

    it('sets lost status after max attempts', () => {
      const game = new CodeBreakerGame('medium');
      game['state'].code = 'AAAA';

      for (let i = 0; i < 10; i++) {
        game.makeGuess('BBBB');
      }

      expect(game.getState().gameStatus).toBe('lost');
    });
  });

  describe('Input Validation', () => {
    it('rejects too short input', () => {
      const game = new CodeBreakerGame('medium');
      const result = game.validateGuess('ABC');
      expect(result.valid).toBe(false);
    });

    it('rejects non-hex characters', () => {
      const game = new CodeBreakerGame('medium');
      const result = game.validateGuess('GHIJ');
      expect(result.valid).toBe(false);
    });

    it('accepts valid hex input', () => {
      const game = new CodeBreakerGame('medium');
      const result = game.validateGuess('CAFE');
      expect(result.valid).toBe(true);
    });

    it('handles case-insensitive input', () => {
      const game = new CodeBreakerGame('medium');
      const result = game.validateGuess('cafe');
      expect(result.valid).toBe(true);
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
│       │   ├── CodeBreakerGame.ts        # Core game logic
│       │   ├── CodeBreakerGame.test.ts   # Unit tests
│       │   └── codebreaker-command.ts    # Terminal integration
│       └── builtins.ts                   # Register command
```

## Integration Steps

1. Implement `CodeBreakerGame` class with full test coverage
2. Implement terminal command wrapper
3. Register command in builtins
4. Add integration tests
5. Test in actual terminal

## Future Enhancements

- [ ] Hint system (reveal one character)
- [ ] Statistics tracking (games played, win rate)
- [ ] Timed mode
- [ ] Multiplayer (two players take turns)
- [ ] Custom code length
- [ ] Sound effects (if desktop app version)

---

## Summary

CodeBreaker uses a clean separation between game logic and UI, making it:
- Highly testable
- Reusable (could be adapted for desktop app)
- Maintainable
- Extensible

The algorithm for checking guesses handles all edge cases including repeated characters, ensuring fair and accurate feedback.
