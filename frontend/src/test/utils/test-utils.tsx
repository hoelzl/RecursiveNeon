/**
 * Custom test utilities for testing React components
 *
 * Provides enhanced render functions and utilities for testing
 * components with various contexts and providers.
 */
import { ReactElement, ReactNode } from 'react';
import { render, RenderOptions } from '@testing-library/react';

/**
 * Custom render function that wraps components with necessary providers
 *
 * @param ui - The component to render
 * @param options - Render options
 * @returns Render result with all utilities
 */
export function renderWithProviders(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) {
  function Wrapper({ children }: { children: ReactNode }) {
    // Add any global providers here (e.g., ServiceProvider, ThemeProvider)
    return <>{children}</>;
  }

  return render(ui, { wrapper: Wrapper, ...options });
}

// Re-export everything from testing library
export * from '@testing-library/react';
export { renderWithProviders as render };
