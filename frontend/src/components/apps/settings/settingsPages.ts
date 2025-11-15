/**
 * Settings Pages Registry
 *
 * Central registry for all settings pages. To add a new settings page:
 * 1. Create a new component (e.g., AudioSettingsPage.tsx)
 * 2. Import it here
 * 3. Add it to the settingsPages array
 *
 * No changes to core settings code are required!
 */

import { ComponentType } from 'react';
import { ClockSettingsPage } from './ClockSettingsPage';
import { ThemeSettingsPage } from './ThemeSettingsPage';

export interface SettingsPage {
  id: string;
  name: string;
  icon: string;
  category?: string;
  component: ComponentType;
  order?: number;
}

export const settingsPages: SettingsPage[] = [
  {
    id: 'clock',
    name: 'Clock',
    icon: '🕐',
    component: ClockSettingsPage,
    order: 1,
  },
  {
    id: 'theme',
    name: 'Theme',
    icon: '🎨',
    component: ThemeSettingsPage,
    order: 2,
  },
  // More pages can be added here...
];

// Sort by category then order
settingsPages.sort((a, b) => {
  if (a.category !== b.category) {
    return (a.category || '').localeCompare(b.category || '');
  }
  return (a.order || 0) - (b.order || 0);
});
