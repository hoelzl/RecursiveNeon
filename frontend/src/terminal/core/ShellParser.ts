/**
 * Shell-like argument parser
 * Handles quotes, escaping, and spaces in arguments
 */

export interface PartialArgumentInfo {
  partial: string;
  isQuoted: boolean;
  quoteChar: '"' | "'" | null;
  startIndex: number;
}

export class ShellParser {
  /**
   * Parse a command line into arguments, respecting quotes and escaping
   *
   * Examples:
   *   'cd Documents' => ['cd', 'Documents']
   *   'cd "My Documents"' => ['cd', 'My Documents']
   *   'cd My\\ Documents' => ['cd', 'My Documents']
   */
  static parseArguments(commandLine: string): string[] {
    const args: string[] = [];
    let currentArg = '';
    let inQuote: '"' | "'" | null = null;
    let escaped = false;

    for (let i = 0; i < commandLine.length; i++) {
      const char = commandLine[i];

      if (escaped) {
        // Previous char was backslash, add this char literally
        currentArg += char;
        escaped = false;
        continue;
      }

      if (char === '\\') {
        // Start escape sequence
        escaped = true;
        continue;
      }

      if (inQuote) {
        // Inside a quoted string
        if (char === inQuote) {
          // Closing quote
          inQuote = null;
        } else {
          currentArg += char;
        }
      } else {
        // Not in a quoted string
        if (char === '"' || char === "'") {
          // Opening quote
          inQuote = char;
        } else if (char === ' ' || char === '\t') {
          // Whitespace - end current argument
          if (currentArg.length > 0) {
            args.push(currentArg);
            currentArg = '';
          }
        } else {
          currentArg += char;
        }
      }
    }

    // Add final argument (even if empty, to handle trailing space)
    if (currentArg.length > 0 || (commandLine.length > 0 && /\s$/.test(commandLine))) {
      args.push(currentArg);
    }

    return args;
  }

  /**
   * Get information about the partial argument being completed
   *
   * Returns the partial argument text, whether it's inside quotes,
   * and where it starts in the command line
   */
  static getPartialArgument(commandLine: string): PartialArgumentInfo {
    let currentArg = '';
    let inQuote: '"' | "'" | null = null;
    let escaped = false;
    let argStartIndex = 0;
    let currentIndex = 0;

    for (let i = 0; i < commandLine.length; i++) {
      const char = commandLine[i];

      if (escaped) {
        currentArg += char;
        escaped = false;
        continue;
      }

      if (char === '\\') {
        escaped = true;
        continue;
      }

      if (inQuote) {
        if (char === inQuote) {
          inQuote = null;
        } else {
          currentArg += char;
        }
      } else {
        if (char === '"' || char === "'") {
          inQuote = char;
          argStartIndex = i + 1; // Start after the quote
        } else if (char === ' ' || char === '\t') {
          if (currentArg.length > 0) {
            currentArg = '';
          }
          argStartIndex = i + 1; // Next argument starts after space
        } else {
          if (currentArg.length === 0) {
            argStartIndex = i;
          }
          currentArg += char;
        }
      }

      currentIndex = i;
    }

    return {
      partial: currentArg,
      isQuoted: inQuote !== null,
      quoteChar: inQuote,
      startIndex: argStartIndex,
    };
  }

  /**
   * Quote a path if it contains spaces or special characters
   *
   * Examples:
   *   'Documents' => 'Documents'
   *   'My Documents' => '"My Documents"'
   *   'file (1).txt' => '"file (1).txt"'
   */
  static quoteIfNeeded(path: string, alreadyQuoted: boolean = false): string {
    // Already quoted, don't double-quote
    if (alreadyQuoted) {
      return path;
    }

    // Check if path needs quoting (contains space or special chars)
    const needsQuoting = /[\s()]/.test(path);

    if (!needsQuoting) {
      return path;
    }

    // Escape existing quotes in the path
    const escapedPath = path.replace(/"/g, '\\"');

    // Wrap in double quotes
    return `"${escapedPath}"`;
  }

  /**
   * Get the argument index at a given cursor position
   */
  static getArgumentIndexAtCursor(commandLine: string, cursorPosition: number): number {
    const lineBeforeCursor = commandLine.substring(0, cursorPosition);
    const args = this.parseArguments(lineBeforeCursor);

    // If line ends with space, we're starting a new argument
    if (lineBeforeCursor.endsWith(' ')) {
      return args.length;
    }

    // Otherwise, we're completing the last argument
    return args.length - 1;
  }

  /**
   * Replace an argument in a command line at a specific index
   */
  static replaceArgument(
    commandLine: string,
    argumentIndex: number,
    newValue: string,
    cursorPosition: number
  ): { newCommandLine: string; newCursorPosition: number } {
    const lineBeforeCursor = commandLine.substring(0, cursorPosition);
    const lineAfterCursor = commandLine.substring(cursorPosition);

    const partialInfo = this.getPartialArgument(lineBeforeCursor);

    // Remove the partial argument and replace with new value
    const before = lineBeforeCursor.substring(0, partialInfo.startIndex);

    // If the partial was quoted, make sure to include the opening quote
    let quotePrefix = '';
    if (partialInfo.isQuoted && partialInfo.quoteChar && partialInfo.startIndex > 0) {
      const charBeforeStart = commandLine[partialInfo.startIndex - 1];
      if (charBeforeStart === partialInfo.quoteChar) {
        quotePrefix = partialInfo.quoteChar;
      }
    }

    const newCommandLine = before + newValue + lineAfterCursor;
    const newCursorPosition = before.length + newValue.length;

    return { newCommandLine, newCursorPosition };
  }
}
