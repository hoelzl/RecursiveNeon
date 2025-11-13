/**
 * Command registry
 * Manages command registration, lookup, and execution
 */

import { Command, CommandContext } from '../types';

export class CommandRegistry {
  private commands: Map<string, Command> = new Map();
  private aliases: Map<string, string> = new Map();

  /**
   * Register a command
   */
  register(command: Command): void {
    this.commands.set(command.name, command);
  }

  /**
   * Register multiple commands
   */
  registerAll(commands: Command[]): void {
    commands.forEach((cmd) => this.register(cmd));
  }

  /**
   * Unregister a command
   */
  unregister(name: string): void {
    this.commands.delete(name);
  }

  /**
   * Get a command by name
   */
  get(name: string): Command | undefined {
    // Check if it's an alias first
    const aliasTarget = this.aliases.get(name);
    if (aliasTarget) {
      // Parse the alias command to get the actual command name
      const parts = aliasTarget.split(/\s+/);
      return this.commands.get(parts[0]);
    }

    return this.commands.get(name);
  }

  /**
   * Get all registered commands
   */
  getAll(): Command[] {
    return Array.from(this.commands.values());
  }

  /**
   * Get all command names
   */
  getNames(): string[] {
    return Array.from(this.commands.keys());
  }

  /**
   * Check if a command exists
   */
  has(name: string): boolean {
    return this.commands.has(name) || this.aliases.has(name);
  }

  /**
   * Register a command alias
   */
  registerAlias(alias: string, target: string): void {
    this.aliases.set(alias, target);
  }

  /**
   * Get all aliases
   */
  getAliases(): Map<string, string> {
    return new Map(this.aliases);
  }

  /**
   * Execute a command
   */
  async execute(commandName: string, context: CommandContext): Promise<void> {
    // Check if it's an alias
    const aliasTarget = this.aliases.get(commandName);
    if (aliasTarget) {
      // Parse the alias and merge args
      const aliasParts = aliasTarget.split(/\s+/);
      const aliasCommand = aliasParts[0];
      const aliasArgs = aliasParts.slice(1);

      // Merge alias args with provided args
      context.args = [...aliasArgs, ...context.args];
      commandName = aliasCommand;
    }

    const command = this.commands.get(commandName);

    if (!command) {
      throw new Error(`Command not found: ${commandName}`);
    }

    // Parse options from args
    const { args, options } = this.parseArgsAndOptions(context.args, command);

    // Update context with parsed values
    context.args = args;
    context.options = options;

    // Execute the command
    await command.execute(context);
  }

  /**
   * Parse arguments and options
   */
  private parseArgsAndOptions(
    args: string[],
    command: Command
  ): { args: string[]; options: Map<string, string | boolean> } {
    const options = new Map<string, string | boolean>();
    const parsedArgs: string[] = [];

    for (let i = 0; i < args.length; i++) {
      const arg = args[i];

      if (arg.startsWith('--')) {
        // Long option (e.g., --help, --version)
        const optionName = arg.substring(2);
        const commandOption = command.options?.find((opt) => opt.flag === `--${optionName}`);

        if (commandOption?.takesValue && i + 1 < args.length) {
          options.set(optionName, args[++i]);
        } else {
          options.set(optionName, true);
        }
      } else if (arg.startsWith('-') && arg.length > 1) {
        // Short option(s) (e.g., -l, -la)
        const flags = arg.substring(1);

        for (const flag of flags) {
          const commandOption = command.options?.find((opt) => opt.flag === `-${flag}`);

          if (commandOption?.takesValue && i + 1 < args.length) {
            options.set(flag, args[++i]);
          } else {
            options.set(flag, true);
          }
        }
      } else {
        // Regular argument
        parsedArgs.push(arg);
      }
    }

    return { args: parsedArgs, options };
  }

  /**
   * Get help text for a command
   */
  getHelp(commandName: string): string {
    const command = this.get(commandName);

    if (!command) {
      return `Command not found: ${commandName}`;
    }

    let help = `${command.name} - ${command.description}\n\n`;
    help += `Usage: ${command.usage}\n`;

    if (command.options && command.options.length > 0) {
      help += `\nOptions:\n`;
      command.options.forEach((opt) => {
        const value = opt.takesValue ? ' <value>' : '';
        help += `  ${opt.flag}${value}  ${opt.description}\n`;
      });
    }

    return help;
  }

  /**
   * Get general help text
   */
  getGeneralHelp(): string {
    let help = 'Available commands:\n\n';

    const commands = Array.from(this.commands.values()).sort((a, b) => a.name.localeCompare(b.name));

    commands.forEach((cmd) => {
      help += `  ${cmd.name.padEnd(15)} ${cmd.description}\n`;
    });

    help += `\nType 'man <command>' for detailed help on a specific command.\n`;

    return help;
  }
}
