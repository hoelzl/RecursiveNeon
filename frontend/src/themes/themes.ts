/**
 * Theme Definitions
 *
 * Defines all available themes for the application.
 */

export interface Theme {
  id: string;
  name: string;
  description: string;
  colors: {
    primary: string;
    secondary: string;
    background: string;
    surface: string;
    text: string;
    textSecondary: string;
    border: string;
    accent: string;
    success: string;
    warning: string;
    error: string;
    taskbarBackground: string;
    windowTitleBar: string;
  };
}

export const themes: Theme[] = [
  {
    id: 'classic',
    name: 'Classic',
    description: 'The original Recursive://Neon theme with cyan accents',
    colors: {
      primary: '#0066CC',
      secondary: '#004999',
      background: '#008080',
      surface: '#C0C0C0',
      text: '#000000',
      textSecondary: '#666666',
      border: '#808080',
      accent: '#00d4ff',
      success: '#00AA00',
      warning: '#FF8800',
      error: '#CC0000',
      taskbarBackground: '#C0C0C0',
      windowTitleBar: '#000080',
    },
  },
  {
    id: 'dark',
    name: 'Dark Mode',
    description: 'Modern dark theme with blue accents',
    colors: {
      primary: '#3391FF',
      secondary: '#1F5FA8',
      background: '#1E1E1E',
      surface: '#2D2D2D',
      text: '#E0E0E0',
      textSecondary: '#A0A0A0',
      border: '#404040',
      accent: '#3391FF',
      success: '#4CAF50',
      warning: '#FF9800',
      error: '#F44336',
      taskbarBackground: '#252525',
      windowTitleBar: '#1E1E1E',
    },
  },
  {
    id: 'light',
    name: 'Light Mode',
    description: 'Clean light theme for daytime use',
    colors: {
      primary: '#2196F3',
      secondary: '#1976D2',
      background: '#FAFAFA',
      surface: '#FFFFFF',
      text: '#212121',
      textSecondary: '#757575',
      border: '#E0E0E0',
      accent: '#2196F3',
      success: '#4CAF50',
      warning: '#FF9800',
      error: '#F44336',
      taskbarBackground: '#F5F5F5',
      windowTitleBar: '#2196F3',
    },
  },
  {
    id: 'neon',
    name: 'Neon',
    description: 'Vibrant neon colors on dark background',
    colors: {
      primary: '#FF00FF',
      secondary: '#CC00CC',
      background: '#000033',
      surface: '#1A1A3E',
      text: '#00FFFF',
      textSecondary: '#FF00FF',
      border: '#FF00FF',
      accent: '#00FFFF',
      success: '#00FF00',
      warning: '#FFFF00',
      error: '#FF0066',
      taskbarBackground: '#0F0F2E',
      windowTitleBar: '#FF00FF',
    },
  },
  {
    id: 'terminal',
    name: 'Terminal',
    description: 'Classic green terminal look',
    colors: {
      primary: '#00FF00',
      secondary: '#00AA00',
      background: '#000000',
      surface: '#0A0A0A',
      text: '#00FF00',
      textSecondary: '#008800',
      border: '#00FF00',
      accent: '#00FF00',
      success: '#00FF00',
      warning: '#FFFF00',
      error: '#FF0000',
      taskbarBackground: '#000000',
      windowTitleBar: '#000000',
    },
  },
  {
    id: 'cyberpunk',
    name: 'Cyberpunk',
    description: 'Cyberpunk aesthetic with purple and cyan',
    colors: {
      primary: '#FF10F0',
      secondary: '#AA00AA',
      background: '#0D001A',
      surface: '#1A0033',
      text: '#F0F0FF',
      textSecondary: '#B0B0FF',
      border: '#FF10F0',
      accent: '#00FFFF',
      success: '#00FF88',
      warning: '#FFAA00',
      error: '#FF0066',
      taskbarBackground: '#1A0033',
      windowTitleBar: '#2D0052',
    },
  },
];

export function getTheme(id: string): Theme | undefined {
  return themes.find(t => t.id === id);
}

/**
 * Apply a theme to the document root
 */
export function applyTheme(themeId: string): void {
  const theme = getTheme(themeId);
  if (!theme) {
    console.error(`Theme '${themeId}' not found`);
    return;
  }

  const root = document.documentElement;

  // Apply CSS variables
  Object.entries(theme.colors).forEach(([key, value]) => {
    const cssVarName = `--${kebabCase(key)}`;
    root.style.setProperty(cssVarName, value);
  });

  console.log(`Applied theme: ${theme.name}`);
}

/**
 * Convert camelCase to kebab-case
 */
function kebabCase(str: string): string {
  return str.replace(/([a-z])([A-Z])/g, '$1-$2').toLowerCase();
}
