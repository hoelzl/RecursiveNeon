import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    // Test environment
    environment: 'jsdom',

    // Setup files to run before each test file
    setupFiles: ['./src/test/setup.ts'],

    // Global test utilities
    globals: true,

    // Coverage configuration
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.d.ts',
        '**/*.config.*',
        '**/mockData',
        'dist/',
      ],
      // Set thresholds (can adjust as tests are added)
      thresholds: {
        lines: 0,
        functions: 0,
        branches: 0,
        statements: 0,
      },
    },

    // Include patterns
    include: ['**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'],

    // Exclude patterns
    exclude: [
      'node_modules',
      'dist',
      '.idea',
      '.git',
      '.cache',
    ],
  },

  // Resolve configuration
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
