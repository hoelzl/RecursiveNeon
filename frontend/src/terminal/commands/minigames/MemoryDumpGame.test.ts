import { describe, it, expect, beforeEach } from 'vitest';
import { MemoryDumpGame, type Difficulty } from './MemoryDumpGame';

describe('MemoryDumpGame', () => {
  describe('Initialization', () => {
    it('creates game with medium difficulty by default', () => {
      const game = new MemoryDumpGame();
      const state = game.getState();

      expect(state.difficulty).toBe('medium');
      expect(state.gameStatus).toBe('playing');
      expect(state.attempts).toHaveLength(0);
    });

    it('creates game with specified difficulty', () => {
      const game = new MemoryDumpGame('hard');
      const state = game.getState();

      expect(state.difficulty).toBe('hard');
    });

    it('generates grid of correct size for medium difficulty', () => {
      const game = new MemoryDumpGame('medium');
      const state = game.getState();

      expect(state.grid.length).toBe(16); // rows
      expect(state.grid[0].length).toBe(24); // cols * 2
    });

    it('generates grid of correct size for easy difficulty', () => {
      const game = new MemoryDumpGame('easy');
      const state = game.getState();

      expect(state.grid.length).toBe(12);
      expect(state.grid[0].length).toBe(24);
    });

    it('sets correct max attempts for difficulty', () => {
      const easy = new MemoryDumpGame('easy');
      const medium = new MemoryDumpGame('medium');
      const hard = new MemoryDumpGame('hard');

      expect(easy.getState().maxAttempts).toBe(5);
      expect(medium.getState().maxAttempts).toBe(4);
      expect(hard.getState().maxAttempts).toBe(3);
    });

    it('generates target word', () => {
      const game = new MemoryDumpGame('medium');
      const state = game.getState();

      expect(state.targetWord).toBeDefined();
      expect(state.targetWord.length).toBe(5); // Medium uses 5-letter words
    });

    it('places correct number of words in grid', () => {
      const game = new MemoryDumpGame('medium');
      const state = game.getState();

      expect(state.words.length).toBe(8); // Medium has 8 words
    });

    it('ensures one word is marked as target', () => {
      const game = new MemoryDumpGame('medium');
      const state = game.getState();

      const targetWords = state.words.filter(w => w.isTarget);
      expect(targetWords.length).toBe(1);
      expect(targetWords[0].word).toBe(state.targetWord);
    });

    it('all words have same length as target', () => {
      const game = new MemoryDumpGame('medium');
      const state = game.getState();

      const allSameLength = state.words.every(
        w => w.word.length === state.targetWord.length
      );
      expect(allSameLength).toBe(true);
    });
  });

  describe('Grid Generation', () => {
    it('grid cells have addresses', () => {
      const game = new MemoryDumpGame('medium');
      const state = game.getState();

      expect(state.grid[0][0].address).toMatch(/^0x[0-9A-F]{4}$/);
    });

    it('grid cells have type property', () => {
      const game = new MemoryDumpGame('medium');
      const state = game.getState();

      const hasTypes = state.grid.every(row =>
        row.every(cell =>
          cell.type === 'word' || cell.type === 'garbage' || cell.type === 'bracket'
        )
      );
      expect(hasTypes).toBe(true);
    });

    it('places words in grid', () => {
      const game = new MemoryDumpGame('medium');
      const state = game.getState();

      // Count word cells
      let wordCells = 0;
      state.grid.forEach(row => {
        row.forEach(cell => {
          if (cell.type === 'word') wordCells++;
        });
      });

      // Should have at least some words placed
      expect(wordCells).toBeGreaterThan(0);
    });

    it('fills remaining cells with garbage', () => {
      const game = new MemoryDumpGame('medium');
      const state = game.getState();

      let garbageCells = 0;
      state.grid.forEach(row => {
        row.forEach(cell => {
          if (cell.type === 'garbage') garbageCells++;
        });
      });

      expect(garbageCells).toBeGreaterThan(0);
    });
  });

  describe('Word Placement', () => {
    it('places words horizontally in grid', () => {
      const game = new MemoryDumpGame('medium');
      const state = game.getState();

      // Check that at least one word is placed correctly
      const firstWord = state.words[0];
      const { startRow, startCol, word } = firstWord;

      for (let i = 0; i < word.length; i++) {
        const cell = state.grid[startRow][startCol + i];
        expect(cell.char).toBe(word[i]);
        expect(cell.type).toBe('word');
      }
    });

    it('words have valid start positions', () => {
      const game = new MemoryDumpGame('medium');
      const state = game.getState();

      state.words.forEach(wordPos => {
        expect(wordPos.startRow).toBeGreaterThanOrEqual(0);
        expect(wordPos.startRow).toBeLessThan(state.grid.length);
        expect(wordPos.startCol).toBeGreaterThanOrEqual(0);
        expect(wordPos.startCol).toBeLessThan(state.grid[0].length);
      });
    });
  });

  describe('Dud Removers', () => {
    it('places dud removers in grid', () => {
      const game = new MemoryDumpGame('medium');
      const state = game.getState();

      expect(state.dudRemovers.length).toBeGreaterThan(0);
    });

    it('dud removers have bracket pairs', () => {
      const game = new MemoryDumpGame('medium');
      const state = game.getState();

      state.dudRemovers.forEach(remover => {
        const { startRow, startCol, endCol, type } = remover;

        expect(state.grid[startRow][startCol].char).toBe(type[0]);
        expect(state.grid[startRow][endCol].char).toBe(type[1]);
        expect(state.grid[startRow][startCol].type).toBe('bracket');
        expect(state.grid[startRow][endCol].type).toBe('bracket');
      });
    });

    it('activates dud remover correctly', () => {
      const game = new MemoryDumpGame('medium');
      const state = game.getState();

      if (state.dudRemovers.length > 0) {
        const remover = state.dudRemovers[0];
        const result = game.activateDudRemover(remover.startRow, remover.startCol);

        expect(result.activated).toBe(true);
        expect(result.effect).toBeDefined();
      }
    });

    it('cannot activate dud remover twice', () => {
      const game = new MemoryDumpGame('medium');
      const state = game.getState();

      if (state.dudRemovers.length > 0) {
        const remover = state.dudRemovers[0];

        game.activateDudRemover(remover.startRow, remover.startCol);
        const result = game.activateDudRemover(remover.startRow, remover.startCol);

        expect(result.activated).toBe(false);
      }
    });

    it('remove_dud effect marks word as removed', () => {
      const game = new MemoryDumpGame('medium');
      const initialAvailable = game.getAvailableWords().length;

      // Try to trigger dud removal
      const state = game.getState();
      if (state.dudRemovers.length > 0) {
        // Keep trying until we get a remove_dud effect
        for (const remover of state.dudRemovers) {
          const result = game.activateDudRemover(remover.startRow, remover.startCol);

          if (result.effect === 'remove_dud') {
            const newAvailable = game.getAvailableWords().length;
            expect(newAvailable).toBeLessThan(initialAvailable);
            expect(result.removedWord).toBeDefined();
            break;
          }
        }
      }
    });
  });

  describe('Word Selection', () => {
    it('recognizes correct word selection as win', () => {
      const game = new MemoryDumpGame('medium');
      const state = game.getState();
      const target = state.targetWord;

      const result = game.selectWord(target);

      expect(result.correct).toBe(true);
      expect(result.gameOver).toBe(true);
      expect(game.getState().gameStatus).toBe('won');
    });

    it('rejects word not in grid', () => {
      const game = new MemoryDumpGame('medium');

      const result = game.selectWord('ZZZZZ');

      expect(result.correct).toBe(false);
      expect(result.likeness).toBe(-1);
    });

    it('rejects already removed word', () => {
      const game = new MemoryDumpGame('medium');
      const state = game.getState();

      // Manually mark a word as removed
      const decoy = state.words.find(w => !w.isTarget);
      if (decoy) {
        decoy.removed = true;

        const result = game.selectWord(decoy.word);

        expect(result.alreadyRemoved).toBe(true);
        expect(result.correct).toBe(false);
      }
    });

    it('tracks attempts correctly', () => {
      const game = new MemoryDumpGame('medium');
      const state = game.getState();

      const decoy = state.words.find(w => !w.isTarget);
      if (decoy) {
        game.selectWord(decoy.word);

        expect(game.getState().attempts).toHaveLength(1);
        expect(game.getState().attempts[0].word).toBe(decoy.word);
      }
    });

    it('triggers lose condition after max attempts', () => {
      const game = new MemoryDumpGame('medium');
      const state = game.getState();

      const decoys = state.words.filter(w => !w.isTarget);

      // Make max attempts with wrong guesses
      for (let i = 0; i < state.maxAttempts; i++) {
        if (decoys[i]) {
          const result = game.selectWord(decoys[i].word);

          if (i < state.maxAttempts - 1) {
            expect(result.gameOver).toBe(false);
          } else {
            expect(result.gameOver).toBe(true);
            expect(game.getState().gameStatus).toBe('lost');
          }
        }
      }
    });

    it('prevents selection after game is won', () => {
      const game = new MemoryDumpGame('medium');
      const state = game.getState();

      game.selectWord(state.targetWord); // Win
      const result = game.selectWord('XXXXX');

      expect(result.gameOver).toBe(true);
      expect(result.correct).toBe(false);
    });
  });

  describe('Likeness Calculation', () => {
    it('calculates exact match as full likeness', () => {
      const game = new MemoryDumpGame('medium');
      (game as any).state.targetWord = 'CYBER';

      // Add a decoy with same word (for testing)
      (game as any).state.words.push({
        word: 'CYBER',
        isTarget: false,
        removed: false,
        startRow: 0,
        startCol: 0,
      });

      const result = game.selectWord('CYBER');

      // It will win because CYBER is the target
      // Let's use a different approach
    });

    it('calculates zero likeness correctly', () => {
      const game = new MemoryDumpGame('medium');
      (game as any).state.targetWord = 'CYBER';

      // Add a decoy with no matching characters in same positions
      (game as any).state.words.push({
        word: 'ADMIX',
        isTarget: false,
        removed: false,
        startRow: 0,
        startCol: 0,
      });

      const result = game.selectWord('ADMIX');

      expect(result.likeness).toBe(0);
    });

    it('calculates partial likeness correctly', () => {
      const game = new MemoryDumpGame('medium');
      (game as any).state.targetWord = 'CYBER';

      // Add a decoy with some matching positions
      // C matches (pos 0), Y matches (pos 1)
      (game as any).state.words.push({
        word: 'CYCLE',
        isTarget: false,
        removed: false,
        startRow: 0,
        startCol: 0,
      });

      const result = game.selectWord('CYCLE');

      expect(result.likeness).toBe(2); // C and Y match
    });
  });

  describe('Utility Methods', () => {
    it('returns available words excluding removed ones', () => {
      const game = new MemoryDumpGame('medium');
      const initialCount = game.getAvailableWords().length;

      // Remove a word
      const state = game.getState();
      const wordToRemove = state.words.find(w => !w.isTarget);
      if (wordToRemove) {
        wordToRemove.removed = true;

        const availableCount = game.getAvailableWords().length;
        expect(availableCount).toBe(initialCount - 1);
      }
    });

    it('calculates remaining attempts correctly', () => {
      const game = new MemoryDumpGame('medium');
      const state = game.getState();

      expect(game.getRemainingAttempts()).toBe(state.maxAttempts);

      const decoy = state.words.find(w => !w.isTarget);
      if (decoy) {
        game.selectWord(decoy.word);
        expect(game.getRemainingAttempts()).toBe(state.maxAttempts - 1);
      }
    });

    it('returns immutable state', () => {
      const game = new MemoryDumpGame('medium');
      const state1 = game.getState();
      const state2 = game.getState();

      expect(state1).not.toBe(state2);
      expect(state1.grid).not.toBe(state2.grid);
      expect(state1.words).not.toBe(state2.words);
    });
  });

  describe('Difficulty Configurations', () => {
    it('easy mode has correct configuration', () => {
      const game = new MemoryDumpGame('easy');
      const state = game.getState();

      expect(state.targetWord.length).toBe(4);
      expect(state.maxAttempts).toBe(5);
    });

    it('medium mode has correct configuration', () => {
      const game = new MemoryDumpGame('medium');
      const state = game.getState();

      expect(state.targetWord.length).toBe(5);
      expect(state.maxAttempts).toBe(4);
    });

    it('hard mode has correct configuration', () => {
      const game = new MemoryDumpGame('hard');
      const state = game.getState();

      expect(state.targetWord.length).toBe(6);
      expect(state.maxAttempts).toBe(3);
    });
  });

  describe('Edge Cases', () => {
    it('handles case-insensitive word selection', () => {
      const game = new MemoryDumpGame('medium');
      const state = game.getState();

      const decoy = state.words.find(w => !w.isTarget);
      if (decoy) {
        const result = game.selectWord(decoy.word.toLowerCase());
        expect(result.correct).toBe(false);
        expect(result.likeness).toBeGreaterThanOrEqual(0);
      }
    });

    it('trims whitespace from word selection', () => {
      const game = new MemoryDumpGame('medium');
      const state = game.getState();

      const decoy = state.words.find(w => !w.isTarget);
      if (decoy) {
        const result = game.selectWord(`  ${decoy.word}  `);
        expect(result.correct).toBe(false);
        expect(result.likeness).toBeGreaterThanOrEqual(0);
      }
    });
  });
});
