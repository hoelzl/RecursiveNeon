/**
 * Built-in terminal commands
 */

import { Command } from '../types';

// ============================================================================
// Helper Functions
// ============================================================================

function formatBytes(bytes: number, decimals: number = 2): string {
  if (bytes === 0) return '0 B';

  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

function formatGrid(items: string[], maxWidth: number = 80): string {
  if (items.length === 0) return '';

  const maxItemLength = Math.max(...items.map((item) => item.length));
  const columnWidth = maxItemLength + 2;
  const columns = Math.floor(maxWidth / columnWidth) || 1;

  let output = '';
  for (let i = 0; i < items.length; i++) {
    output += items[i].padEnd(columnWidth);
    if ((i + 1) % columns === 0) {
      output += '\n';
    }
  }

  if (items.length % columns !== 0) {
    output += '\n';
  }

  return output;
}

// ============================================================================
// Commands
// ============================================================================

export const lsCommand: Command = {
  name: 'ls',
  description: 'List directory contents',
  usage: 'ls [OPTIONS] [PATH]',
  options: [
    { flag: '-l', description: 'Use long listing format' },
    { flag: '-a', description: 'Show hidden files' },
    { flag: '-h', description: 'Human-readable file sizes' },
  ],

  async execute(context) {
    const { session, args, options } = context;
    const fs = session.getFileSystem();
    const path = args[0] || session.getWorkingDirectory();

    const longFormat = options.has('l');
    const showHidden = options.has('a');
    const humanReadable = options.has('h');

    try {
      const resolvedPath = fs.resolvePath(path, session.getWorkingDirectory());
      const nodes = await fs.listDirectory(resolvedPath);

      if (nodes.length === 0) {
        return;
      }

      // Filter hidden files if not showing all
      const filtered = showHidden ? nodes : nodes.filter((n) => !n.name.startsWith('.'));

      if (longFormat) {
        // Long format
        filtered.forEach((node) => {
          const type = node.type === 'directory' ? 'd' : '-';
          const size = node.type === 'file' ? (humanReadable ? formatBytes(node.content?.length || 0) : String(node.content?.length || 0)) : '-';
          const name = node.name;

          session.writeLine(`${type} ${size.padStart(10)} ${name}`, {
            color: node.type === 'directory' ? 'var(--terminal-cyan, #00ffff)' : undefined,
          });
        });
      } else {
        // Grid format
        const names = filtered.map((node) => {
          return node.type === 'directory' ? node.name + '/' : node.name;
        });
        session.write(formatGrid(names, 80));
      }
    } catch (error: any) {
      session.writeError(`ls: ${error.message}`);
    }
  },

  async complete(context) {
    // Complete directory paths
    const fs = context.session.getFileSystem();
    const cwd = context.session.getWorkingDirectory();

    try {
      const nodes = await fs.listDirectory(cwd);
      return nodes.filter((n) => n.type === 'directory').map((n) => n.name);
    } catch {
      return [];
    }
  },
};

export const cdCommand: Command = {
  name: 'cd',
  description: 'Change directory',
  usage: 'cd [PATH]',

  async execute(context) {
    const { session, args } = context;
    const path = args[0] || '/';

    try {
      await session.changeDirectory(path);
    } catch (error: any) {
      session.writeError(`cd: ${error.message}`);
    }
  },

  async complete(context) {
    // Complete directory paths
    const fs = context.session.getFileSystem();
    const cwd = context.session.getWorkingDirectory();

    try {
      const nodes = await fs.listDirectory(cwd);
      return nodes.filter((n) => n.type === 'directory').map((n) => n.name);
    } catch {
      return [];
    }
  },
};

export const pwdCommand: Command = {
  name: 'pwd',
  description: 'Print working directory',
  usage: 'pwd',

  execute(context) {
    const { session } = context;
    session.writeLine(session.getWorkingDirectory());
  },
};

export const catCommand: Command = {
  name: 'cat',
  description: 'Display file contents',
  usage: 'cat <file>',

  async execute(context) {
    const { session, args } = context;

    if (args.length === 0) {
      session.writeError('cat: missing file operand');
      return;
    }

    const fs = session.getFileSystem();

    for (const arg of args) {
      try {
        const resolvedPath = fs.resolvePath(arg, session.getWorkingDirectory());
        const content = await fs.readFile(resolvedPath);
        session.writeLine(content);
      } catch (error: any) {
        session.writeError(`cat: ${error.message}`);
      }
    }
  },

  async complete(context) {
    // Complete file paths
    const fs = context.session.getFileSystem();
    const cwd = context.session.getWorkingDirectory();

    try {
      const nodes = await fs.listDirectory(cwd);
      return nodes.map((n) => n.name);
    } catch {
      return [];
    }
  },
};

export const mkdirCommand: Command = {
  name: 'mkdir',
  description: 'Create directory',
  usage: 'mkdir <directory>',
  options: [{ flag: '-p', description: 'Create parent directories as needed' }],

  async execute(context) {
    const { session, args, options } = context;

    if (args.length === 0) {
      session.writeError('mkdir: missing operand');
      return;
    }

    const fs = session.getFileSystem();
    const createParents = options.has('p');

    for (const arg of args) {
      try {
        const resolvedPath = fs.resolvePath(arg, session.getWorkingDirectory());

        if (createParents) {
          // Create parent directories
          const parts = resolvedPath.split('/').filter((p) => p);
          let currentPath = '';

          for (const part of parts) {
            currentPath += '/' + part;
            const exists = await fs.exists(currentPath);

            if (!exists) {
              await fs.createDirectory(currentPath);
            }
          }
        } else {
          await fs.createDirectory(resolvedPath);
        }
      } catch (error: any) {
        session.writeError(`mkdir: ${error.message}`);
      }
    }
  },
};

export const rmCommand: Command = {
  name: 'rm',
  description: 'Remove files or directories',
  usage: 'rm [OPTIONS] <file>...',
  options: [
    { flag: '-r', description: 'Remove directories recursively' },
    { flag: '-f', description: 'Force removal without confirmation' },
  ],

  async execute(context) {
    const { session, args, options } = context;

    if (args.length === 0) {
      session.writeError('rm: missing operand');
      return;
    }

    const fs = session.getFileSystem();
    const recursive = options.has('r');

    for (const arg of args) {
      try {
        const resolvedPath = fs.resolvePath(arg, session.getWorkingDirectory());
        const node = await fs.findByPath(resolvedPath);

        if (!node) {
          session.writeError(`rm: cannot remove '${arg}': No such file or directory`);
          continue;
        }

        if (node.type === 'directory' && !recursive) {
          session.writeError(`rm: cannot remove '${arg}': Is a directory`);
          continue;
        }

        await fs.delete(resolvedPath);
      } catch (error: any) {
        session.writeError(`rm: ${error.message}`);
      }
    }
  },
};

export const mvCommand: Command = {
  name: 'mv',
  description: 'Move or rename files',
  usage: 'mv <source> <destination>',

  async execute(context) {
    const { session, args } = context;

    if (args.length < 2) {
      session.writeError('mv: missing file operand');
      return;
    }

    const fs = session.getFileSystem();
    const source = args[0];
    const dest = args[1];

    try {
      const sourcePath = fs.resolvePath(source, session.getWorkingDirectory());
      const destPath = fs.resolvePath(dest, session.getWorkingDirectory());

      await fs.move(sourcePath, destPath);
    } catch (error: any) {
      session.writeError(`mv: ${error.message}`);
    }
  },
};

export const cpCommand: Command = {
  name: 'cp',
  description: 'Copy files',
  usage: 'cp [OPTIONS] <source> <destination>',
  options: [{ flag: '-r', description: 'Copy directories recursively' }],

  async execute(context) {
    const { session, args } = context;

    if (args.length < 2) {
      session.writeError('cp: missing file operand');
      return;
    }

    const fs = session.getFileSystem();
    const source = args[0];
    const dest = args[1];

    try {
      const sourcePath = fs.resolvePath(source, session.getWorkingDirectory());
      const destPath = fs.resolvePath(dest, session.getWorkingDirectory());

      await fs.copy(sourcePath, destPath);
    } catch (error: any) {
      session.writeError(`cp: ${error.message}`);
    }
  },
};

export const touchCommand: Command = {
  name: 'touch',
  description: 'Create empty file',
  usage: 'touch <file>',

  async execute(context) {
    const { session, args } = context;

    if (args.length === 0) {
      session.writeError('touch: missing file operand');
      return;
    }

    const fs = session.getFileSystem();

    for (const arg of args) {
      try {
        const resolvedPath = fs.resolvePath(arg, session.getWorkingDirectory());
        const exists = await fs.exists(resolvedPath);

        if (!exists) {
          await fs.createFile(resolvedPath, '', 'text/plain');
        }
      } catch (error: any) {
        session.writeError(`touch: ${error.message}`);
      }
    }
  },
};

export const echoCommand: Command = {
  name: 'echo',
  description: 'Display a line of text',
  usage: 'echo [text...]',

  execute(context) {
    const { session, args } = context;
    const text = args.join(' ');

    // Support $VAR expansion
    const expanded = text.replace(/\$(\w+)/g, (match, varName) => {
      return (session.getEnv(varName) as string) || match;
    });

    session.writeLine(expanded);
  },
};

export const clearCommand: Command = {
  name: 'clear',
  description: 'Clear the terminal screen',
  usage: 'clear',

  execute(context) {
    const { session } = context;
    session.clearScreen();
  },
};

export const helpCommand: Command = {
  name: 'help',
  description: 'Display available commands',
  usage: 'help [command]',

  execute(context) {
    const { session, args } = context;
    const registry = (context as any).registry;

    if (!registry) {
      session.writeError('help: command registry not available');
      return;
    }

    if (args.length > 0) {
      // Show help for specific command
      const help = registry.getHelp(args[0]);
      session.writeLine(help);
    } else {
      // Show general help
      const help = registry.getGeneralHelp();
      session.writeLine(help);
    }
  },
};

export const manCommand: Command = {
  name: 'man',
  description: 'Display command manual',
  usage: 'man <command>',

  execute(context) {
    const { session, args } = context;
    const registry = (context as any).registry;

    if (!registry) {
      session.writeError('man: command registry not available');
      return;
    }

    if (args.length === 0) {
      session.writeError('man: missing command name');
      return;
    }

    const help = registry.getHelp(args[0]);
    session.writeLine(help);
  },
};

export const historyCommand: Command = {
  name: 'history',
  description: 'Display command history',
  usage: 'history',

  execute(context) {
    const { session } = context;
    const history = session.getHistory();

    history.forEach((cmd, index) => {
      session.writeLine(`  ${(index + 1).toString().padStart(4)}  ${cmd}`);
    });
  },
};

export const whoamiCommand: Command = {
  name: 'whoami',
  description: 'Print current user name',
  usage: 'whoami',

  execute(context) {
    const { session } = context;
    const user = session.getEnv('USER') as string;
    session.writeLine(user || 'unknown');
  },
};

export const hostnameCommand: Command = {
  name: 'hostname',
  description: 'Print system hostname',
  usage: 'hostname',

  execute(context) {
    const { session } = context;
    session.writeLine('neon');
  },
};

export const dateCommand: Command = {
  name: 'date',
  description: 'Display current date and time',
  usage: 'date',

  execute(context) {
    const { session } = context;
    const now = new Date();
    session.writeLine(now.toLocaleString());
  },
};

export const envCommand: Command = {
  name: 'env',
  description: 'Display environment variables',
  usage: 'env',

  execute(context) {
    const { session } = context;
    const env = session.getEnv() as Map<string, string>;

    env.forEach((value, key) => {
      session.writeLine(`${key}=${value}`);
    });
  },
};

// ============================================================================
// Export all built-in commands
// ============================================================================

export const builtinCommands: Command[] = [
  lsCommand,
  cdCommand,
  pwdCommand,
  catCommand,
  mkdirCommand,
  rmCommand,
  mvCommand,
  cpCommand,
  touchCommand,
  echoCommand,
  clearCommand,
  helpCommand,
  manCommand,
  historyCommand,
  whoamiCommand,
  hostnameCommand,
  dateCommand,
  envCommand,
];
