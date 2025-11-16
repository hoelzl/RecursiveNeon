/**
 * Tab completion engine
 * Handles command, path, and option completion
 */

import { CompletionResult, CompletionContext } from '../types';
import { CommandRegistry } from './CommandRegistry';
import { TerminalSession } from './TerminalSession';
import { ArgumentParser } from './ArgumentParser';

export class CompletionEngine {
  private registry: CommandRegistry;
  private argParser: ArgumentParser;

  constructor(registry: CommandRegistry, argParser: ArgumentParser) {
    this.registry = registry;
    this.argParser = argParser;
  }

  /**
   * Complete a command line
   */
  async complete(session: TerminalSession, commandLine: string, cursorPosition: number): Promise<CompletionResult> {
    // Trim the line up to cursor
    const lineBeforeCursor = commandLine.substring(0, cursorPosition);


    if (lineBeforeCursor.trim() === '') {
      // Empty line - complete command names
      return this.completeCommand('');
    }

    // Parse the command line using ArgumentParser
    const parsed = this.argParser.parseCommandLine(lineBeforeCursor);
    const partialArg = this.argParser.getPartialArg(commandLine, cursorPosition);


    // Check if we're completing the command name (first word)
    const isFirstWord = parsed.args.length === 0 && !lineBeforeCursor.endsWith(' ');

    if (isFirstWord) {
      // Completing the command name
      return this.completeCommand(parsed.command);
    }

    const commandName = parsed.command;
    const command = this.registry.get(commandName);

    // If it's an option (starts with -)
    if (partialArg.value.startsWith('-')) {
      if (command && command.options) {
        return this.completeOption(partialArg.value, command.options, partialArg.startIndex, cursorPosition);
      }
      return { completions: [], prefix: '', commonPrefix: '', replaceStart: cursorPosition, replaceEnd: cursorPosition };
    }

    // Try command-specific completion
    if (command && command.complete) {
      const context: CompletionContext = {
        session,
        commandLine,
        cursorPosition,
        api: session.getAPI(),
        partialArg: partialArg.value,
      };

      try {
        const completions = await command.complete(context);
        return this.buildCompletionResult(partialArg.value, completions, partialArg.startIndex, cursorPosition, true);
      } catch (error) {
        console.error('Command completion error:', error);
      }
    }

    // Default: try path completion
    return await this.completePath(session, partialArg.value, partialArg.startIndex, cursorPosition);
  }

  /**
   * Complete command names
   */
  private completeCommand(partial: string): CompletionResult {
    const commandNames = this.registry.getNames();
    const aliases = Array.from(this.registry.getAliases().keys());
    const allNames = [...commandNames, ...aliases];

    const matches = allNames.filter((name) => name.startsWith(partial));

    return this.buildCompletionResult(partial, matches, 0, partial.length, false);
  }

  /**
   * Complete command options
   */
  private completeOption(
    partial: string,
    options: Array<{ flag: string; description: string }>,
    replaceStart: number,
    replaceEnd: number
  ): CompletionResult {
    const matches = options.map((opt) => opt.flag).filter((flag) => flag.startsWith(partial));

    return this.buildCompletionResult(partial, matches, replaceStart, replaceEnd, false);
  }

  /**
   * Complete file/directory paths
   */
  private async completePath(
    session: TerminalSession,
    partial: string,
    replaceStart: number,
    replaceEnd: number
  ): Promise<CompletionResult> {
    const fs = session.getFileSystem();
    const cwd = session.getWorkingDirectory();


    try {
      // Determine the directory to search
      let searchDir = cwd;
      let filePrefix = partial;

      // Special handling for . and .. (current and parent directory references)
      // These need to be resolved even without a trailing slash
      if (partial === '.' || partial === '..') {
        searchDir = fs.resolvePath(partial, cwd);
        filePrefix = '';
      } else if (partial.includes('/')) {
        // Path contains directory separator
        const lastSlash = partial.lastIndexOf('/');
        const dirPart = partial.substring(0, lastSlash + 1);
        filePrefix = partial.substring(lastSlash + 1);

        // Resolve the directory part (which may contain . or ..)
        searchDir = fs.resolvePath(dirPart, cwd);
      }

      // List directory contents
      const nodes = await fs.listDirectory(searchDir);

      // Filter by prefix
      const matches = nodes
        .filter((node) => node.name.startsWith(filePrefix))
        .map((node) => {
          // Add trailing slash for directories
          return node.type === 'directory' ? node.name + '/' : node.name;
        });

      // Build full paths by combining basePath with matches
      const basePath = partial.substring(0, partial.length - filePrefix.length);
      const fullPaths = matches.map((match) => basePath + match);


      // Quote full paths if needed (don't quote individual components)
      const quotedPaths = fullPaths.map((path) => this.argParser.quoteIfNeeded(path));


      // Build the completion result
      if (quotedPaths.length === 0) {
        return {
          completions: [],
          prefix: partial,
          commonPrefix: partial,
          replaceStart,
          replaceEnd,
        };
      }

      if (quotedPaths.length === 1) {
        return {
          completions: quotedPaths,
          prefix: partial,
          commonPrefix: quotedPaths[0],
          replaceStart,
          replaceEnd,
        };
      }

      // Find common prefix among all quoted paths
      const commonPrefix = this.findCommonPrefix(quotedPaths);

      return {
        completions: quotedPaths.sort(),
        prefix: partial,
        commonPrefix,
        replaceStart,
        replaceEnd,
      };
    } catch (error) {
      // Directory doesn't exist or error occurred
      return {
        completions: [],
        prefix: partial,
        commonPrefix: partial,
        replaceStart,
        replaceEnd,
      };
    }
  }

  /**
   * Build completion result from matches
   */
  private buildCompletionResult(
    partial: string,
    matches: string[],
    replaceStart: number,
    replaceEnd: number,
    quoteIfNeeded: boolean
  ): CompletionResult {
    if (matches.length === 0) {
      return {
        completions: [],
        prefix: partial,
        commonPrefix: partial,
        replaceStart,
        replaceEnd,
      };
    }

    // Quote matches if needed (for filenames with spaces)
    const quotedMatches = quoteIfNeeded
      ? matches.map((m) => this.argParser.quoteIfNeeded(m))
      : matches;

    if (quotedMatches.length === 1) {
      return {
        completions: quotedMatches,
        prefix: partial,
        commonPrefix: quotedMatches[0],
        replaceStart,
        replaceEnd,
      };
    }

    // Find common prefix among all matches
    const commonPrefix = this.findCommonPrefix(quotedMatches);

    return {
      completions: quotedMatches.sort(),
      prefix: partial,
      commonPrefix,
      replaceStart,
      replaceEnd,
    };
  }

  /**
   * Find the longest common prefix among strings
   */
  private findCommonPrefix(strings: string[]): string {
    if (strings.length === 0) return '';
    if (strings.length === 1) return strings[0];

    let prefix = strings[0];

    for (let i = 1; i < strings.length; i++) {
      while (!strings[i].startsWith(prefix)) {
        prefix = prefix.substring(0, prefix.length - 1);
        if (prefix === '') {
          return '';
        }
      }
    }

    return prefix;
  }
}
