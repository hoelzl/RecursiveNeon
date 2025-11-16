import type { Command, CommandContext } from '../../core/CommandRegistry';
import { MemoryDumpGame, type Difficulty, type GridCell } from './MemoryDumpGame';

/**
 * MemoryDump Terminal Command
 *
 * Integrates the MemoryDump game with the terminal system.
 */

function parseDifficulty(args: string[]): Difficulty {
  const difficultyArg = args.find(arg =>
    arg === 'easy' || arg === 'medium' || arg === 'hard'
  );

  if (difficultyArg === 'easy' || difficultyArg === 'medium' || difficultyArg === 'hard') {
    return difficultyArg;
  }

  const diffIndex = args.indexOf('--difficulty');
  if (diffIndex !== -1 && args[diffIndex + 1]) {
    const diff = args[diffIndex + 1].toLowerCase();
    if (diff === 'easy' || diff === 'medium' || diff === 'hard') {
      return diff;
    }
  }

  return 'medium';
}

function displayWelcome(context: CommandContext): void {
  const { session } = context;

  session.writeLine('');
  session.writeLine('\x1b[32m╔════════════════════════════════════════════════╗\x1b[0m');
  session.writeLine('\x1b[32m║  ROBCO INDUSTRIES (TM) TERMLINK PROTOCOL     ║\x1b[0m');
  session.writeLine('\x1b[32m║  ENTER PASSWORD NOW                           ║\x1b[0m');
  session.writeLine('\x1b[32m╚════════════════════════════════════════════════╝\x1b[0m');
  session.writeLine('');
}

function displayGrid(context: CommandContext, grid: GridCell[][], colsPerSide: number): void {
  const { session } = context;

  for (let r = 0; r < grid.length; r++) {
    // Left column
    session.write(`\x1b[90m${grid[r][0].address}\x1b[0m  `);

    for (let c = 0; c < colsPerSide; c++) {
      const cell = grid[r][c];
      const color = getCellColor(cell);
      session.write(`\x1b[${color}m${cell.char}\x1b[0m`);
    }

    session.write('  '); // Space between columns

    // Right column
    session.write(`\x1b[90m${grid[r][colsPerSide].address}\x1b[0m  `);

    for (let c = colsPerSide; c < grid[r].length; c++) {
      const cell = grid[r][c];
      const color = getCellColor(cell);
      session.write(`\x1b[${color}m${cell.char}\x1b[0m`);
    }

    session.writeLine('');
  }
}

function getCellColor(cell: GridCell): string {
  if (cell.type === 'word') return '32'; // Green
  if (cell.type === 'bracket') return '33'; // Yellow
  return '90'; // Gray (garbage)
}

function displayStatus(context: CommandContext, game: MemoryDumpGame): void {
  const { session } = context;
  const state = game.getState();
  const remaining = game.getRemainingAttempts();

  session.writeLine('');

  // Display attempts remaining as blocks
  const blocks = '\x1b[36m█\x1b[0m'.repeat(remaining);
  const emptyBlocks = '░'.repeat(state.maxAttempts - remaining);
  session.writeLine(`Attempts Remaining: ${blocks}${emptyBlocks}`);

  session.writeLine('');

  // Display previous attempts
  if (state.attempts.length > 0) {
    session.writeLine('Previous Attempts:');
    state.attempts.forEach(attempt => {
      const wordLength = state.targetWord.length;
      session.writeLine(
        `  \x1b[33m>\x1b[0m ${attempt.word.padEnd(10)} Likeness: ${attempt.likeness}/${wordLength}`
      );
    });
    session.writeLine('');
  }
}

function displayGameEnd(context: CommandContext, game: MemoryDumpGame): void {
  const { session } = context;
  const state = game.getState();

  session.writeLine('');

  if (state.gameStatus === 'won') {
    session.writeLine('\x1b[32m>>> ACCESS GRANTED <<<\x1b[0m');
    session.writeLine(`Entry granted. Password: \x1b[1m${state.targetWord}\x1b[0m`);
    session.writeLine('System unlocked.');
  } else {
    session.writeLine('\x1b[31m>>> TERMINAL LOCKED <<<\x1b[0m');
    session.writeLine('Intrusion detected. Tracing connection...');
    session.writeLine(`The password was: \x1b[1m${state.targetWord}\x1b[0m`);
  }

  session.writeLine('');
}

function displayHelp(context: CommandContext): void {
  const { session } = context;

  session.writeLine('');
  session.writeLine('How to play:');
  session.writeLine('  - Enter a word from the grid to guess the password');
  session.writeLine('  - Likeness shows how many letters match in the same position');
  session.writeLine('  - Words are highlighted in \x1b[32mgreen\x1b[0m in the grid');
  session.writeLine('  - Bracket pairs \x1b[33m[]\x1b[0m can remove duds or restore attempts');
  session.writeLine('  - Type "help" to see this message');
  session.writeLine('  - Type "quit" or "exit" to leave the game');
  session.writeLine('');
}

export const memorydumpCommand: Command = {
  name: 'memorydump',
  description: 'Play the MemoryDump hacking game - find the password',
  usage: 'memorydump [easy|medium|hard]',

  async execute(context: CommandContext): Promise<number> {
    const { session, args } = context;

    const difficulty = parseDifficulty(args);
    const game = new MemoryDumpGame(difficulty);
    const state = game.getState();

    // Calculate columns per side
    const colsPerSide = state.grid[0].length / 2;

    // Display welcome and initial state
    displayWelcome(context);
    displayGrid(context, state.grid, colsPerSide);
    displayStatus(context, game);

    session.writeLine('Type "help" for instructions.');
    session.writeLine('');

    // Game loop
    while (game.getState().gameStatus === 'playing') {
      const input = await session.readLine('\x1b[32m[MEMORYDUMP]>\x1b[0m ');

      const trimmed = input.trim();
      const normalized = trimmed.toUpperCase();

      // Handle commands
      if (trimmed.toLowerCase() === 'quit' || trimmed.toLowerCase() === 'exit') {
        session.writeLine('\n\x1b[33mConnection terminated.\x1b[0m\n');
        return 0;
      }

      if (trimmed.toLowerCase() === 'help') {
        displayHelp(context);
        // Re-display grid and status after help
        displayGrid(context, game.getState().grid, colsPerSide);
        displayStatus(context, game);
        continue;
      }

      // Check if input is empty
      if (!trimmed) {
        continue;
      }

      // Try to select word
      const availableWords = game.getAvailableWords();

      if (availableWords.includes(normalized)) {
        const result = game.selectWord(normalized);

        if (result.alreadyRemoved) {
          session.writeLine('\x1b[33m> Dud removed.\x1b[0m');
          session.writeLine('');
          // Re-display grid and status
          displayGrid(context, game.getState().grid, colsPerSide);
          displayStatus(context, game);
          continue;
        }

        if (result.correct) {
          // Win!
          displayGameEnd(context, game);
          break;
        } else {
          // Wrong guess, show likeness
          session.writeLine('');
          session.writeLine(`\x1b[31m> Entry denied.\x1b[0m`);
          session.writeLine(`\x1b[33m> Likeness=${result.likeness}\x1b[0m`);
          session.writeLine('');

          // Check if game over
          if (result.gameOver) {
            displayGameEnd(context, game);
            break;
          }

          // Re-display grid and status so they're always visible
          displayGrid(context, game.getState().grid, colsPerSide);
          displayStatus(context, game);
        }
      } else {
        // Not a valid word, maybe trying to use dud remover?
        session.writeLine('\x1b[31m> Error: Not a valid word.\x1b[0m');
        session.writeLine('  Type one of the \x1b[32mgreen\x1b[0m words from the grid.');
        session.writeLine('');
      }
    }

    return 0;
  },
};
