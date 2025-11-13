/**
 * Tab completion engine
 * Handles command, path, and option completion
 */

import { CompletionResult, CompletionContext } from '../types';
import { CommandRegistry } from './CommandRegistry';
import { TerminalSession } from './TerminalSession';

export class CompletionEngine {
  private registry: CommandRegistry;

  constructor(registry: CommandRegistry) {
    this.registry = registry;
  }

  /**
   * Complete a command line
   */
  async complete(session: TerminalSession, commandLine: string, cursorPosition: number): Promise<CompletionResult> {
    // Trim the line up to cursor
    const lineBeforeCursor = commandLine.substring(0, cursorPosition);
    const parts = lineBeforeCursor.split(/\s+/);

    if (parts.length === 0 || lineBeforeCursor.trim() === '') {
      // Empty line - complete command names
      return this.completeCommand('');
    }

    const commandName = parts[0];
    const isFirstWord = parts.length === 1 && !lineBeforeCursor.endsWith(' ');

    if (isFirstWord) {
      // Completing the command name
      return this.completeCommand(commandName);
    }

    // Get the partial argument being completed
    const partialArg = lineBeforeCursor.endsWith(' ') ? '' : parts[parts.length - 1];
    const command = this.registry.get(commandName);

    // If it's an option (starts with -)
    if (partialArg.startsWith('-')) {
      if (command && command.options) {
        return this.completeOption(partialArg, command.options);
      }
      return { completions: [], prefix: '', commonPrefix: '' };
    }

    // Try command-specific completion
    if (command && command.complete) {
      const context: CompletionContext = {
        session,
        commandLine,
        cursorPosition,
        api: session.getAPI(),
        partialArg,
      };

      try {
        const completions = await command.complete(context);
        return this.buildCompletionResult(partialArg, completions);
      } catch (error) {
        console.error('Command completion error:', error);
      }
    }

    // Default: try path completion
    return await this.completePath(session, partialArg);
  }

  /**
   * Complete command names
   */
  private completeCommand(partial: string): CompletionResult {
    const commandNames = this.registry.getNames();
    const aliases = Array.from(this.registry.getAliases().keys());
    const allNames = [...commandNames, ...aliases];

    const matches = allNames.filter((name) => name.startsWith(partial));

    return this.buildCompletionResult(partial, matches);
  }

  /**
   * Complete command options
   */
  private completeOption(partial: string, options: Array<{ flag: string; description: string }>): CompletionResult {
    const matches = options.map((opt) => opt.flag).filter((flag) => flag.startsWith(partial));

    return this.buildCompletionResult(partial, matches);
  }

  /**
   * Complete file/directory paths
   */
  private async completePath(session: TerminalSession, partial: string): Promise<CompletionResult> {
    const fs = session.getFileSystem();
    const cwd = session.getWorkingDirectory();

    try {
      // Determine the directory to search
      let searchDir = cwd;
      let filePrefix = partial;

      if (partial.includes('/')) {
        // Path contains directory separator
        const lastSlash = partial.lastIndexOf('/');
        const dirPart = partial.substring(0, lastSlash + 1);
        filePrefix = partial.substring(lastSlash + 1);

        // Resolve the directory part
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

      // Build the result with proper prefix
      const basePath = partial.substring(0, partial.length - filePrefix.length);
      const result = this.buildCompletionResult(filePrefix, matches);

      // Adjust prefix, commonPrefix, and completions to include the base path
      result.prefix = basePath + result.prefix;
      result.commonPrefix = basePath + result.commonPrefix;
      result.completions = result.completions.map((c) => basePath + c);

      return result;
    } catch (error) {
      // Directory doesn't exist or error occurred
      return { completions: [], prefix: partial, commonPrefix: partial };
    }
  }

  /**
   * Build completion result from matches
   */
  private buildCompletionResult(partial: string, matches: string[]): CompletionResult {
    if (matches.length === 0) {
      return {
        completions: [],
        prefix: partial,
        commonPrefix: partial,
      };
    }

    if (matches.length === 1) {
      return {
        completions: matches,
        prefix: partial,
        commonPrefix: matches[0],
      };
    }

    // Find common prefix among all matches
    const commonPrefix = this.findCommonPrefix(matches);

    return {
      completions: matches.sort(),
      prefix: partial,
      commonPrefix,
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
