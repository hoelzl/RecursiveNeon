import { describe, it, expect, beforeEach } from 'vitest';
import { PortScannerGame, type Difficulty } from './PortScannerGame';

describe('PortScannerGame', () => {
  describe('Initialization', () => {
    it('creates game with medium difficulty by default', () => {
      const game = new PortScannerGame();
      const state = game.getState();

      expect(state.difficulty).toBe('medium');
      expect(state.gameStatus).toBe('idle');
      expect(state.revealedCount).toBe(0);
    });

    it('generates grid with correct dimensions for each difficulty', () => {
      const easy = new PortScannerGame('easy');
      const medium = new PortScannerGame('medium');
      const hard = new PortScannerGame('hard');

      expect(easy.getState().grid.length).toBe(8);
      expect(easy.getState().grid[0].length).toBe(8);

      expect(medium.getState().grid.length).toBe(10);
      expect(medium.getState().grid[0].length).toBe(10);

      expect(hard.getState().grid.length).toBe(12);
      expect(hard.getState().grid[0].length).toBe(12);
    });

    it('places correct number of open ports', () => {
      const game = new PortScannerGame('easy');
      const state = game.getState();
      let portCount = 0;

      for (const row of state.grid) {
        for (const cell of row) {
          if (cell.isOpenPort) portCount++;
        }
      }

      expect(portCount).toBe(10); // Easy mode has 10 ports
    });

    it('calculates adjacent ports correctly', () => {
      const game = new PortScannerGame('easy');
      const state = game.getState();

      // Find a cell and verify its adjacency count is correct
      for (const row of state.grid) {
        for (const cell of row) {
          if (!cell.isOpenPort) {
            let expectedAdjacent = 0;

            // Count manually
            for (let dr = -1; dr <= 1; dr++) {
              for (let dc = -1; dc <= 1; dc++) {
                if (dr === 0 && dc === 0) continue;

                const nr = cell.row + dr;
                const nc = cell.col + dc;

                if (nr >= 0 && nr < state.rows && nc >= 0 && nc < state.cols) {
                  if (state.grid[nr][nc].isOpenPort) {
                    expectedAdjacent++;
                  }
                }
              }
            }

            expect(cell.adjacentPorts).toBe(expectedAdjacent);
          }
        }
      }
    });
  });

  describe('Cell Reveal', () => {
    it('reveals cell on first click', () => {
      const game = new PortScannerGame('easy');

      const result = game.revealCell(0, 0);

      expect(result.success).toBe(true);
      expect(game.getState().gameStatus).toBe('playing');
      expect(game.getState().grid[0][0].isRevealed).toBe(true);
    });

    it('starts game on first click', () => {
      const game = new PortScannerGame('easy');

      expect(game.getState().gameStatus).toBe('idle');
      expect(game.getState().startTime).toBeNull();

      game.revealCell(0, 0);

      expect(game.getState().gameStatus).toBe('playing');
      expect(game.getState().startTime).not.toBeNull();
    });

    it('first click is always safe', () => {
      const game = new PortScannerGame('easy');

      // Click multiple times, first click should never hit a port
      for (let i = 0; i < 10; i++) {
        const freshGame = new PortScannerGame('easy');
        const result = freshGame.revealCell(0, 0);

        // First click should reveal a safe cell (may auto-reveal more)
        expect(result.hitPort).toBe(false);
      }
    });

    it('cannot reveal already revealed cell', () => {
      const game = new PortScannerGame('easy');

      game.revealCell(0, 0);
      const result = game.revealCell(0, 0);

      expect(result.success).toBe(false);
    });

    it('cannot reveal flagged cell', () => {
      const game = new PortScannerGame('easy');

      game.toggleFlag(0, 0);
      const result = game.revealCell(0, 0);

      expect(result.success).toBe(false);
    });

    it('reveals open port and adds to score', () => {
      const game = new PortScannerGame('easy');
      const state = game.getState();

      // Find an open port
      let portCell: { row: number; col: number } | null = null;
      for (const row of state.grid) {
        for (const cell of row) {
          if (cell.isOpenPort) {
            portCell = { row: cell.row, col: cell.col };
            break;
          }
        }
        if (portCell) break;
      }

      if (portCell) {
        // Make first click safe
        game.revealCell(5, 5);

        const initialScore = game.getState().score;
        const result = game.revealCell(portCell.row, portCell.col);

        expect(result.hitPort).toBe(true);
        expect(game.getState().score).toBeGreaterThan(initialScore);
      }
    });

    it('auto-reveals adjacent cells with zero adjacent ports', () => {
      const game = new PortScannerGame('easy');

      // Find a cell with 0 adjacent ports
      const state = game.getState();
      let zeroCell: { row: number; col: number } | null = null;

      for (const row of state.grid) {
        for (const cell of row) {
          if (!cell.isOpenPort && cell.adjacentPorts === 0) {
            zeroCell = { row: cell.row, col: cell.col };
            break;
          }
        }
        if (zeroCell) break;
      }

      if (zeroCell) {
        const result = game.revealCell(zeroCell.row, zeroCell.col);

        // Should auto-reveal some cells
        expect(result.autoRevealed.length).toBeGreaterThan(0);
      }
    });
  });

  describe('Flagging', () => {
    it('toggles flag on cell', () => {
      const game = new PortScannerGame('easy');

      const result = game.toggleFlag(0, 0);

      expect(result).toBe(true);
      expect(game.getState().grid[0][0].isFlagged).toBe(true);
      expect(game.getState().flaggedCount).toBe(1);
    });

    it('toggles flag off', () => {
      const game = new PortScannerGame('easy');

      game.toggleFlag(0, 0);
      game.toggleFlag(0, 0);

      expect(game.getState().grid[0][0].isFlagged).toBe(false);
      expect(game.getState().flaggedCount).toBe(0);
    });

    it('cannot flag revealed cell', () => {
      const game = new PortScannerGame('easy');

      game.revealCell(0, 0);
      const result = game.toggleFlag(0, 0);

      expect(result).toBe(false);
    });

    it('adds bonus for correct flag', () => {
      const game = new PortScannerGame('easy');
      const state = game.getState();

      // Find an open port
      let portCell: { row: number; col: number } | null = null;
      for (const row of state.grid) {
        for (const cell of row) {
          if (cell.isOpenPort) {
            portCell = { row: cell.row, col: cell.col };
            break;
          }
        }
        if (portCell) break;
      }

      if (portCell) {
        const initialScore = game.getState().score;
        game.toggleFlag(portCell.row, portCell.col);

        expect(game.getState().score).toBeGreaterThan(initialScore);
      }
    });
  });

  describe('Win Condition', () => {
    it('detects win when all ports found', () => {
      const game = new PortScannerGame('easy');
      const state = game.getState();

      // Reveal/flag all ports
      for (const row of state.grid) {
        for (const cell of row) {
          if (cell.isOpenPort) {
            game.toggleFlag(cell.row, cell.col);
          }
        }
      }

      expect(game.getState().gameStatus).toBe('won');
    });

    it('adds time bonus on win', () => {
      const game = new PortScannerGame('easy');
      const state = game.getState();

      // Start game
      game.revealCell(0, 0);

      const scoreBeforeWin = game.getState().score;

      // Win immediately
      for (const row of state.grid) {
        for (const cell of row) {
          if (cell.isOpenPort) {
            game.toggleFlag(cell.row, cell.col);
          }
        }
      }

      // Score should increase (time bonus)
      expect(game.getState().score).toBeGreaterThan(scoreBeforeWin);
    });
  });

  describe('Game Reset', () => {
    it('resets game to initial state', () => {
      const game = new PortScannerGame('easy');

      // Play a bit
      game.revealCell(0, 0);
      game.toggleFlag(1, 1);

      // Reset
      game.reset();

      const state = game.getState();
      expect(state.gameStatus).toBe('idle');
      expect(state.revealedCount).toBe(0);
      expect(state.flaggedCount).toBe(0);
      expect(state.score).toBe(0);
      expect(state.startTime).toBeNull();
    });
  });

  describe('State Immutability', () => {
    it('returns immutable state', () => {
      const game = new PortScannerGame('easy');
      const state1 = game.getState();
      const state2 = game.getState();

      expect(state1).not.toBe(state2);
      expect(state1.grid).not.toBe(state2.grid);
    });
  });
});
