/**
 * Word lists for MemoryDump game
 * Organized by word length for difficulty scaling
 */

export const WORD_LISTS: Record<number, string[]> = {
  4: [
    'BYTE', 'DATA', 'CODE', 'PORT', 'CORE', 'LOOP', 'DISK', 'LINK',
    'NODE', 'SYNC', 'HASH', 'KEYS', 'BITS', 'FLOW', 'TASK', 'CALL',
    'BOOT', 'ROOT', 'PATH', 'FILE', 'LOAD', 'SCAN', 'PING', 'HOST',
  ],

  5: [
    'CYBER', 'PROXY', 'VIRUS', 'PROBE', 'TRACE', 'FRAME', 'PIXEL',
    'LOGIC', 'ADMIN', 'DEBUG', 'CLOCK', 'CACHE', 'LOGIN', 'SHELL',
    'STACK', 'QUEUE', 'INDEX', 'PARSE', 'QUERY', 'SCOPE', 'TOKEN',
    'BOARD', 'POWER', 'INPUT', 'ERROR', 'FLASH', 'CHUNK', 'SLEEP',
  ],

  6: [
    'SYSTEM', 'PACKET', 'ROUTER', 'HACKER', 'KERNEL', 'DAEMON', 'VECTOR',
    'BINARY', 'THREAD', 'SOCKET', 'MEMORY', 'BUFFER', 'CIPHER', 'STREAM',
    'SERVER', 'CLIENT', 'MODULE', 'PYTHON', 'SCRIPT', 'OUTPUT', 'OBJECT',
    'STRUCT', 'SIGNAL', 'SENSOR', 'BRIDGE', 'SWITCH', 'FILTER', 'MATRIX',
  ],

  7: [
    'PROGRAM', 'NETWORK', 'DIGITAL', 'PROCESS', 'GATEWAY', 'ENCRYPT',
    'DECRYPT', 'COMMAND', 'CONSOLE', 'CAPTURE', 'COMPILE', 'EXECUTE',
    'MACHINE', 'POINTER', 'SEGMENT', 'ADDRESS', 'RUNTIME', 'VIRTUAL',
    'CLUSTER', 'CHANNEL', 'SESSION', 'ADAPTER', 'FIREWALL', 'CONTROL',
  ],

  8: [
    'TERMINAL', 'PROTOCOL', 'DATABASE', 'PASSWORD', 'OVERFLOW', 'BACKBONE',
    'TRANSFER', 'FUNCTION', 'VARIABLE', 'OPERATOR', 'REGISTER', 'COMPUTER',
    'INTERNET', 'SOFTWARE', 'HARDWARE', 'PLATFORM', 'COMPILER', 'DEBUGGER',
    'MAINFRAME', 'FIRMWARE', 'TRANSMIT', 'RECEIVER', 'SECURITY', 'BACKDOOR',
  ],
};

/**
 * Get random words of a specific length
 */
export function getRandomWords(
  length: number,
  count: number
): { target: string; decoys: string[] } {
  const wordList = WORD_LISTS[length];

  if (!wordList || wordList.length < count) {
    throw new Error(`Not enough words of length ${length}`);
  }

  // Shuffle word list
  const shuffled = [...wordList].sort(() => Math.random() - 0.5);

  const target = shuffled[0];
  const decoys = shuffled.slice(1, count);

  return { target, decoys };
}
