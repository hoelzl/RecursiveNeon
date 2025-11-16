import { describe, it, expect, beforeEach, vi } from 'vitest';
import { CodeBreakerGame, type Difficulty } from './CodeBreakerGame';

describe('CodeBreakerGame', () => {
  describe('Initialization', () => {
    it('creates game with medium difficulty by default', () => {
      const game = new CodeBreakerGame();
      const state = game.getState();

      expect(state.difficulty).toBe('medium');
      expect(state.gameStatus).toBe('playing');
      expect(state.guesses).toHaveLength(0);
    });

    it('creates game with specified difficulty', () => {
      const game = new CodeBreakerGame('hard');
      const state = game.getState();

      expect(state.difficulty).toBe('hard');
      expect(state.code).toHaveLength(6); // Hard mode has 6 characters
    });

    it('generates code of correct length for easy difficulty', () => {
      const game = new CodeBreakerGame('easy');
      expect(game.getState().code).toHaveLength(4);
    });

    it('generates code of correct length for hard difficulty', () => {
      const game = new CodeBreakerGame('hard');
      expect(game.getState().code).toHaveLength(6);
    });

    it('generates code with valid hex characters', () => {
      const game = new CodeBreakerGame('medium');
      const code = game.getState().code;

      expect(code).toMatch(/^[0-9A-F]+$/);
    });

    it('sets correct max attempts for difficulty', () => {
      const easy = new CodeBreakerGame('easy');
      const medium = new CodeBreakerGame('medium');
      const hard = new CodeBreakerGame('hard');

      expect(easy.getState().maxAttempts).toBe(12);
      expect(medium.getState().maxAttempts).toBe(10);
      expect(hard.getState().maxAttempts).toBe(8);
    });
  });

  describe('Input Validation', () => {
    let game: CodeBreakerGame;

    beforeEach(() => {
      game = new CodeBreakerGame('medium');
    });

    it('accepts valid hex code of correct length', () => {
      const result = game.validateGuess('CAFE');
      expect(result.valid).toBe(true);
      expect(result.error).toBeUndefined();
    });

    it('accepts valid code in lowercase', () => {
      const result = game.validateGuess('cafe');
      expect(result.valid).toBe(true);
    });

    it('accepts code with whitespace (trims it)', () => {
      const result = game.validateGuess('  DEAD  ');
      expect(result.valid).toBe(true);
    });

    it('rejects code that is too short', () => {
      const result = game.validateGuess('ABC');
      expect(result.valid).toBe(false);
      expect(result.error).toContain('exactly 4 characters');
    });

    it('rejects code that is too long', () => {
      const result = game.validateGuess('ABCDE');
      expect(result.valid).toBe(false);
      expect(result.error).toContain('exactly 4 characters');
    });

    it('rejects code with invalid characters', () => {
      const result = game.validateGuess('GHIJ');
      expect(result.valid).toBe(false);
      expect(result.error).toContain('valid characters');
    });

    it('rejects code with special characters', () => {
      const result = game.validateGuess('AB@D');
      expect(result.valid).toBe(false);
    });
  });

  describe('Guess Checking - Exact Matches', () => {
    it('identifies all exact matches correctly', () => {
      const game = new CodeBreakerGame('medium');
      // Inject known code for testing
      (game as any).state.code = 'CAFE';

      const result = game.makeGuess('CAFE');

      expect(result.feedback).toHaveLength(4);
      expect(result.feedback.every(f => f.status === 'exact')).toBe(true);
      expect(game.getState().gameStatus).toBe('won');
    });

    it('identifies partial exact matches correctly', () => {
      const game = new CodeBreakerGame('medium');
      (game as any).state.code = 'CAFE';

      const result = game.makeGuess('CADE');

      expect(result.feedback[0].status).toBe('exact'); // C
      expect(result.feedback[1].status).toBe('exact'); // A
      expect(result.feedback[2].status).toBe('miss');  // D (not in code)
      expect(result.feedback[3].status).toBe('exact'); // E
    });
  });

  describe('Guess Checking - Partial Matches', () => {
    it('identifies partial matches (all correct chars, wrong positions)', () => {
      const game = new CodeBreakerGame('medium');
      (game as any).state.code = 'CAFE';

      const result = game.makeGuess('EFAC');

      // All characters are in the code but in wrong positions
      expect(result.feedback.every(f => f.status === 'partial')).toBe(true);
    });

    it('identifies mixed exact and partial matches', () => {
      const game = new CodeBreakerGame('medium');
      (game as any).state.code = 'CAFE';

      const result = game.makeGuess('FACE');

      expect(result.feedback[0].status).toBe('partial'); // F is in code but wrong position
      expect(result.feedback[1].status).toBe('exact');   // A is exact
      expect(result.feedback[2].status).toBe('partial'); // C is in code but wrong position
      expect(result.feedback[3].status).toBe('exact');   // E is exact
    });
  });

  describe('Guess Checking - Misses', () => {
    it('identifies all misses correctly', () => {
      const game = new CodeBreakerGame('medium');
      (game as any).state.code = 'CAFE';

      const result = game.makeGuess('1234');

      expect(result.feedback.every(f => f.status === 'miss')).toBe(true);
    });

    it('handles mixed matches and misses', () => {
      const game = new CodeBreakerGame('medium');
      (game as any).state.code = 'CAFE';

      const result = game.makeGuess('C123');

      expect(result.feedback[0].status).toBe('exact'); // C is exact
      expect(result.feedback[1].status).toBe('miss');  // 1 not in code
      expect(result.feedback[2].status).toBe('miss');  // 2 not in code
      expect(result.feedback[3].status).toBe('miss');  // 3 not in code
    });
  });

  describe('Guess Checking - Repeated Characters', () => {
    it('handles repeated characters in code correctly (all same)', () => {
      const game = new CodeBreakerGame('medium');
      (game as any).state.code = 'AAAA';

      const result = game.makeGuess('AAAB');

      expect(result.feedback[0].status).toBe('exact'); // A exact
      expect(result.feedback[1].status).toBe('exact'); // A exact
      expect(result.feedback[2].status).toBe('exact'); // A exact
      expect(result.feedback[3].status).toBe('miss');  // B miss
    });

    it('handles repeated characters in guess correctly', () => {
      const game = new CodeBreakerGame('medium');
      (game as any).state.code = 'ABCD';

      const result = game.makeGuess('AAAA');

      // Only one A in code, so only first A should match
      expect(result.feedback[0].status).toBe('exact'); // A exact (position 0)
      expect(result.feedback[1].status).toBe('miss');  // A miss (no more A's in code)
      expect(result.feedback[2].status).toBe('miss');  // A miss
      expect(result.feedback[3].status).toBe('miss');  // A miss
    });

    it('handles complex repeated character scenario', () => {
      const game = new CodeBreakerGame('medium');
      (game as any).state.code = 'AABB';

      const result = game.makeGuess('ABAB');

      expect(result.feedback[0].status).toBe('exact');   // A exact (pos 0)
      expect(result.feedback[1].status).toBe('partial'); // B partial (in code, wrong pos)
      expect(result.feedback[2].status).toBe('partial'); // A partial (in code, wrong pos)
      expect(result.feedback[3].status).toBe('exact');   // B exact (pos 3)
    });
  });

  describe('Game State Management', () => {
    it('starts with playing status', () => {
      const game = new CodeBreakerGame('medium');
      expect(game.getState().gameStatus).toBe('playing');
    });

    it('tracks guesses correctly', () => {
      const game = new CodeBreakerGame('medium');
      (game as any).state.code = 'CAFE';

      game.makeGuess('DEAD');
      game.makeGuess('BEEF');

      const state = game.getState();
      expect(state.guesses).toHaveLength(2);
      expect(state.guesses[0].input).toBe('DEAD');
      expect(state.guesses[1].input).toBe('BEEF');
    });

    it('sets won status when code is guessed', () => {
      const game = new CodeBreakerGame('medium');
      (game as any).state.code = 'DEAD';

      game.makeGuess('DEAD');

      expect(game.getState().gameStatus).toBe('won');
    });

    it('sets lost status after max attempts', () => {
      const game = new CodeBreakerGame('medium');
      (game as any).state.code = 'AAAA';
      (game as any).state.maxAttempts = 3;

      game.makeGuess('BBBB');
      game.makeGuess('CCCC');
      game.makeGuess('DDDD');

      expect(game.getState().gameStatus).toBe('lost');
    });

    it('throws error when making guess after game is won', () => {
      const game = new CodeBreakerGame('medium');
      (game as any).state.code = 'CAFE';

      game.makeGuess('CAFE');

      expect(() => game.makeGuess('DEAD')).toThrow('not in playing state');
    });

    it('throws error when making guess after game is lost', () => {
      const game = new CodeBreakerGame('medium');
      (game as any).state.code = 'AAAA';
      (game as any).state.maxAttempts = 1;

      game.makeGuess('BBBB');

      expect(() => game.makeGuess('CCCC')).toThrow('not in playing state');
    });
  });

  describe('Utility Methods', () => {
    it('returns correct code length', () => {
      const medium = new CodeBreakerGame('medium');
      const hard = new CodeBreakerGame('hard');

      expect(medium.getCodeLength()).toBe(4);
      expect(hard.getCodeLength()).toBe(6);
    });

    it('calculates remaining attempts correctly', () => {
      const game = new CodeBreakerGame('medium');
      (game as any).state.code = 'CAFE';

      expect(game.getRemainingAttempts()).toBe(10);

      game.makeGuess('DEAD');
      expect(game.getRemainingAttempts()).toBe(9);

      game.makeGuess('BEEF');
      expect(game.getRemainingAttempts()).toBe(8);
    });

    it('returns immutable state', () => {
      const game = new CodeBreakerGame('medium');
      const state1 = game.getState();
      const state2 = game.getState();

      // Should be different objects (immutable)
      expect(state1).not.toBe(state2);
      expect(state1.guesses).not.toBe(state2.guesses);
    });
  });

  describe('Edge Cases', () => {
    it('handles empty code gracefully', () => {
      const game = new CodeBreakerGame('medium');
      // Empty code would mean game is misconfigured, but validation is based on expected length
      // So "CAFE" is still valid input format even if code is empty
      const result = game.validateGuess('CAFE');
      expect(result.valid).toBe(true); // Input format is valid
    });

    it('handles first guess correctly', () => {
      const game = new CodeBreakerGame('medium');
      (game as any).state.code = 'CAFE';

      const result = game.makeGuess('CAFE');

      expect(result).toBeDefined();
      expect(game.getState().guesses).toHaveLength(1);
    });

    it('normalizes guess to uppercase', () => {
      const game = new CodeBreakerGame('medium');
      (game as any).state.code = 'CAFE';

      const result = game.makeGuess('cafe');

      expect(result.input).toBe('CAFE');
    });

    it('trims whitespace from guess', () => {
      const game = new CodeBreakerGame('medium');
      (game as any).state.code = 'CAFE';

      const result = game.makeGuess('  CAFE  ');

      expect(result.input).toBe('CAFE');
    });
  });

  describe('Difficulty Configurations', () => {
    it('easy mode uses only decimal digits', () => {
      const game = new CodeBreakerGame('easy');
      const code = game.getState().code;

      expect(code).toMatch(/^[0-9]+$/);
    });

    it('medium and hard modes use hex digits', () => {
      const medium = new CodeBreakerGame('medium');
      const hard = new CodeBreakerGame('hard');

      // Just verify they use the full hex charset
      expect(medium.validateGuess('ABCD').valid).toBe(true);
      expect(hard.validateGuess('ABCDEF').valid).toBe(true);
    });

    it('different difficulties have different attempt limits', () => {
      const easy = new CodeBreakerGame('easy');
      const medium = new CodeBreakerGame('medium');
      const hard = new CodeBreakerGame('hard');

      expect(easy.getRemainingAttempts()).toBe(12);
      expect(medium.getRemainingAttempts()).toBe(10);
      expect(hard.getRemainingAttempts()).toBe(8);
    });
  });
});
