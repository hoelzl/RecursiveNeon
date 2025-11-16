import type { Command, CommandContext } from '../../core/CommandRegistry';
import { CodeBreakerGame, type Difficulty, type Guess } from './CodeBreakerGame';

/**
 * CodeBreaker Terminal Command
 *
 * Integrates the CodeBreaker game with the terminal system.
 */

function parseDifficulty(args: string[]): Difficulty {
  const difficultyArg = args.find(arg =>
    arg === 'easy' || arg === 'medium' || arg === 'hard'
  );

  if (difficultyArg === 'easy' || difficultyArg === 'medium' || difficultyArg === 'hard') {
    return difficultyArg;
  }

  // Check for --difficulty flag
  const diffIndex = args.indexOf('--difficulty');
  if (diffIndex !== -1 && args[diffIndex + 1]) {
    const diff = args[diffIndex + 1].toLowerCase();
    if (diff === 'easy' || diff === 'medium' || diff === 'hard') {
      return diff;
    }
  }

  return 'medium'; // default
}

function displayWelcome(context: CommandContext, game: CodeBreakerGame): void {
  const { session } = context;
  const state = game.getState();

  session.writeLine('╔══════════════════════════════════════╗');
  session.writeLine('║       CODEBREAKER v1.0              ║');
  session.writeLine('║   Crack the hex code                ║');
  session.writeLine('╚══════════════════════════════════════╝');
  session.writeLine('');
  session.writeLine(`Difficulty: ${state.difficulty.toUpperCase()}`);
  session.writeLine(`Code length: ${game.getCodeLength()} characters`);
  session.writeLine(`Attempts: ${state.maxAttempts}`);
  session.writeLine('');
  session.writeLine('Feedback guide:');
  session.writeLine('  \x1b[32m✓\x1b[0m (Green)  = Correct position');
  session.writeLine('  \x1b[33m⚬\x1b[0m (Yellow) = Wrong position');
  session.writeLine('  \x1b[90m✗\x1b[0m (Gray)   = Not in code');
  session.writeLine('');
  session.writeLine('Type your guess and press Enter. Type "quit" to exit.');
  session.writeLine('');
}

function displayGuessResult(
  context: CommandContext,
  guess: Guess,
  game: CodeBreakerGame
): void {
  const { session } = context;
  const state = game.getState();
  const guessNumber = state.guesses.length;
  const remainingAttempts = game.getRemainingAttempts();

  session.writeLine('');
  session.write(`Guess ${guessNumber}: `);

  // Display feedback with colors
  guess.feedback.forEach((fb) => {
    let colorCode: string;
    let symbol: string;

    if (fb.status === 'exact') {
      colorCode = '\x1b[32m'; // Green
      symbol = '✓';
    } else if (fb.status === 'partial') {
      colorCode = '\x1b[33m'; // Yellow
      symbol = '⚬';
    } else {
      colorCode = '\x1b[90m'; // Gray
      symbol = '✗';
    }

    session.write(`${colorCode}[${fb.char}${symbol}]\x1b[0m`);
  });

  session.writeLine('');

  const exactCount = guess.feedback.filter(f => f.status === 'exact').length;
  const partialCount = guess.feedback.filter(f => f.status === 'partial').length;

  session.writeLine(`  ${exactCount} exact, ${partialCount} partial`);

  if (state.gameStatus === 'playing') {
    session.writeLine(`Attempts remaining: ${remainingAttempts}`);
  }

  session.writeLine('');
}

function displayGameEnd(context: CommandContext, game: CodeBreakerGame): void {
  const { session } = context;
  const state = game.getState();

  session.writeLine('');

  if (state.gameStatus === 'won') {
    session.writeLine('🎉 \x1b[32mACCESS GRANTED\x1b[0m 🎉');
    session.writeLine(`Code cracked in ${state.guesses.length} attempts!`);
  } else {
    session.writeLine('❌ \x1b[31mACCESS DENIED\x1b[0m ❌');
    session.writeLine('System locked.');
  }

  session.writeLine(`The code was: \x1b[1m${state.code}\x1b[0m`);
  session.writeLine('');
}

export const codebreakerCommand: Command = {
  name: 'codebreaker',
  description: 'Play the CodeBreaker hacking game - guess the hex code',
  usage: 'codebreaker [easy|medium|hard]',

  async execute(context: CommandContext): Promise<number> {
    const { session, args } = context;

    // Parse difficulty
    const difficulty = parseDifficulty(args);

    // Create game instance
    const game = new CodeBreakerGame(difficulty);

    // Display welcome
    displayWelcome(context, game);

    // Game loop
    while (game.getState().gameStatus === 'playing') {
      const input = await session.readLine('Enter your guess: ');

      // Check for quit
      if (input.toLowerCase().trim() === 'quit' || input.toLowerCase().trim() === 'exit') {
        session.writeLine('\nGame aborted.');
        return 0;
      }

      // Validate input
      const validation = game.validateGuess(input);
      if (!validation.valid) {
        session.writeLine(`\x1b[31mError: ${validation.error}\x1b[0m`);
        continue; // Don't count as an attempt
      }

      // Make guess
      try {
        const result = game.makeGuess(input.toUpperCase().trim());
        displayGuessResult(context, result, game);

        // Check if game ended
        if (game.getState().gameStatus !== 'playing') {
          displayGameEnd(context, game);
          break;
        }
      } catch (error) {
        if (error instanceof Error) {
          session.writeLine(`\x1b[31mError: ${error.message}\x1b[0m`);
        }
        break;
      }
    }

    return 0;
  },
};
