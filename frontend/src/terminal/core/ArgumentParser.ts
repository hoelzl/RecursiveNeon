/**
 * Argument parser for command lines
 * Handles quoted strings, escape characters, and proper argument splitting
 */

export interface ParsedCommand {
  command: string;
  args: string[];
}

export interface ParsedArguments {
  args: string[];
  tokens: ParseToken[];
}

export interface ParseToken {
  value: string;
  startIndex: number;
  endIndex: number;
  quoted: boolean;
  quoteChar?: '"' | "'";
}

/**
 * Parse a command line into command name and arguments
 * Supports:
 * - Single quotes: 'text with spaces'
 * - Double quotes: "text with spaces"
 * - Backslash escaping: \  for literal space, \", \', \\
 */
export class ArgumentParser {
  /**
   * Parse a full command line into command and arguments
   */
  parseCommandLine(commandLine: string): ParsedCommand {
    const trimmed = commandLine.trim();
    if (!trimmed) {
      return { command: '', args: [] };
    }

    const { args } = this.parseArguments(trimmed);

    if (args.length === 0) {
      return { command: '', args: [] };
    }

    return {
      command: args[0],
      args: args.slice(1),
    };
  }

  /**
   * Parse arguments from a string (without extracting command)
   * Returns both the parsed args and detailed token information
   */
  parseArguments(input: string): ParsedArguments {
    const args: string[] = [];
    const tokens: ParseToken[] = [];
    let currentArg = '';
    let currentArgStart = -1;
    let inQuote: '"' | "'" | null = null;
    let wasQuoted = false; // Track if any part of the arg was quoted
    let lastQuoteChar: '"' | "'" | undefined = undefined; // Track the quote char that was used
    let escaped = false;
    let i = 0;

    const finishArg = (endIndex: number) => {
      if (currentArg !== '' || inQuote !== null || wasQuoted) {
        args.push(currentArg);
        tokens.push({
          value: currentArg,
          startIndex: currentArgStart,
          endIndex,
          quoted: wasQuoted || inQuote !== null,
          quoteChar: inQuote || lastQuoteChar,
        });
        currentArg = '';
        currentArgStart = -1;
        inQuote = null;
        wasQuoted = false;
        lastQuoteChar = undefined;
      }
    };

    while (i < input.length) {
      const char = input[i];

      // Mark start of argument if needed
      if (currentArgStart === -1 && !this.isWhitespace(char)) {
        currentArgStart = i;
      }

      if (escaped) {
        // Previous character was backslash - add current char literally
        currentArg += char;
        escaped = false;
      } else if (char === '\\') {
        // Start escape sequence
        escaped = true;
      } else if (inQuote) {
        // Inside quotes
        if (char === inQuote) {
          // End quote - but don't finish arg, just exit quote mode
          wasQuoted = true;
          lastQuoteChar = inQuote;
          inQuote = null;
        } else {
          // Add character to current argument
          currentArg += char;
        }
      } else if (char === '"' || char === "'") {
        // About to start a new quote
        if (wasQuoted) {
          // We ended a previous quote, now starting a new one
          // Finish the previous argument
          finishArg(i - 1);
        }
        // Start quote
        inQuote = char;
        if (currentArgStart === -1) {
          currentArgStart = i;
        }
      } else if (this.isWhitespace(char)) {
        // Whitespace outside quotes - end current argument
        finishArg(i - 1);
      } else {
        // Regular character
        currentArg += char;
      }

      i++;
    }

    // Handle trailing backslash
    if (escaped) {
      currentArg += '\\';
    }

    // Finish last argument
    if (currentArg !== '' || inQuote !== null || wasQuoted) {
      finishArg(input.length - 1);
    }

    return { args, tokens };
  }

  /**
   * Find the argument token at a specific cursor position
   */
  findTokenAtPosition(input: string, position: number): ParseToken | null {
    // Parse up to the cursor position to see what's been typed
    const substr = input.substring(0, position);
    const beforeTokens = this.parseArguments(substr);

    if (beforeTokens.tokens.length === 0) {
      return null;
    }

    // If we're at end of input and cursor is after whitespace, return empty token
    if (position >= input.length && substr.length > 0 && this.isWhitespace(substr[substr.length - 1])) {
      return {
        value: '',
        startIndex: position,
        endIndex: position - 1,
        quoted: false,
      };
    }

    const lastToken = beforeTokens.tokens[beforeTokens.tokens.length - 1];

    // If cursor is in the middle of a word, look ahead to find the complete token
    // by parsing the full string and finding the token at this position
    if (position < input.length && !this.isWhitespace(input[position])) {
      const fullTokens = this.parseArguments(input);

      // Find the token that contains this position
      for (const token of fullTokens.tokens) {
        if (position > token.startIndex && position <= token.endIndex) {
          // Return the portion of this token up to the cursor
          // The offset is just the position itself (for cases like 'cmd argument' at position 7)
          const offset = position;
          return {
            value: token.value.substring(0, offset),
            startIndex: token.startIndex,
            endIndex: token.endIndex,  // Use the full token's endIndex for replacement
            quoted: token.quoted,
            quoteChar: token.quoteChar,
          };
        }
      }
    }

    // Return the last token from what we've parsed so far
    return lastToken;
  }

  /**
   * Quote a string if it contains spaces or special characters
   */
  quoteIfNeeded(str: string, forceQuote: boolean = false): string {
    // Check if quoting is needed
    const needsQuoting = forceQuote ||
      str.includes(' ') ||
      str.includes('\t') ||
      str.includes('"') ||
      str.includes("'") ||
      str.includes('\\') ||
      str.includes('$') ||
      str.includes('`') ||
      str.includes('*') ||
      str.includes('?') ||
      str.includes('[') ||
      str.includes(']');

    if (!needsQuoting) {
      return str;
    }

    // Prefer single quotes unless the string contains single quotes
    if (!str.includes("'")) {
      return `'${str}'`;
    }

    // Use double quotes and escape any double quotes inside
    const escaped = str.replace(/\\/g, '\\\\').replace(/"/g, '\\"');
    return `"${escaped}"`;
  }

  /**
   * Check if a character is whitespace
   */
  private isWhitespace(char: string): boolean {
    return char === ' ' || char === '\t' || char === '\n' || char === '\r';
  }

  /**
   * Get the partial argument being typed at cursor position
   * Returns the argument value and whether it's quoted
   */
  getPartialArg(commandLine: string, cursorPosition: number): {
    value: string;
    quoted: boolean;
    quoteChar?: '"' | "'";
    startIndex: number;
  } {
    const token = this.findTokenAtPosition(commandLine, cursorPosition);

    if (!token) {
      return {
        value: '',
        quoted: false,
        startIndex: cursorPosition,
      };
    }

    return {
      value: token.value,
      quoted: token.quoted,
      quoteChar: token.quoteChar,
      startIndex: token.startIndex,
    };
  }

  /**
   * Replace the argument at cursor position with a new value
   * Handles proper quoting
   */
  replaceArgAtCursor(
    commandLine: string,
    cursorPosition: number,
    newValue: string,
    addSpace: boolean = true
  ): { newCommandLine: string; newCursorPosition: number } {
    const token = this.findTokenAtPosition(commandLine, cursorPosition);

    if (!token) {
      // No token at cursor - just append
      const quoted = this.quoteIfNeeded(newValue);
      const space = addSpace ? ' ' : '';
      return {
        newCommandLine: commandLine + quoted + space,
        newCursorPosition: commandLine.length + quoted.length + space.length,
      };
    }

    // Determine what to replace
    let startPos = token.startIndex;
    let endPos = token.endIndex + 1;

    // If the token is quoted, we need to include the quotes in the replacement
    if (token.quoted && token.quoteChar) {
      // Check if there's a quote before startPos
      if (startPos > 0 && commandLine[startPos - 1] === token.quoteChar) {
        startPos--;
      }
      // Check if there's a quote at endPos
      if (endPos < commandLine.length && commandLine[endPos] === token.quoteChar) {
        endPos++;
      }
    }

    // Quote the new value if needed
    const quotedValue = this.quoteIfNeeded(newValue);

    // Build new command line
    const before = commandLine.substring(0, startPos);
    let after = commandLine.substring(endPos);

    // Handle spacing
    if (addSpace) {
      // Ensure there's a space after quotedValue
      if (after.length === 0) {
        // At end of line, add trailing space
        after = ' ';
      } else if (!this.isWhitespace(after[0])) {
        // Not at whitespace, add space before after
        after = ' ' + after;
      }
      // else: after already starts with whitespace, keep it
    } else {
      // Remove any whitespace between quotedValue and after
      after = after.trimStart();
    }

    const newCommandLine = before + quotedValue + after;
    // Cursor should be right after quotedValue (and after space if present)
    const hasSpaceAfter = after.length > 0 && this.isWhitespace(after[0]);
    const newCursorPosition = before.length + quotedValue.length + (hasSpaceAfter ? 1 : 0);

    return { newCommandLine, newCursorPosition };
  }
}
