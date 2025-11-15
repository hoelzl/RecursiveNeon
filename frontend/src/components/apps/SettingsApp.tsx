/**
 * Settings App
 *
 * Centralized settings management with extensible page system.
 * New settings pages can be easily added via the settingsPages registry.
 */

import { useState } from 'react';
import { settingsPages } from './settings/settingsPages';
import './SettingsApp.css';

export function SettingsApp() {
  const [selectedPageId, setSelectedPageId] = useState(settingsPages[0]?.id || '');

  const selectedPage = settingsPages.find(p => p.id === selectedPageId);
  const PageComponent = selectedPage?.component;

  // Group pages by category
  const categorized: Record<string, typeof settingsPages> = {};
  const uncategorized: typeof settingsPages = [];

  settingsPages.forEach(page => {
    if (page.category) {
      if (!categorized[page.category]) {
        categorized[page.category] = [];
      }
      categorized[page.category].push(page);
    } else {
      uncategorized.push(page);
    }
  });

  return (
    <div className="settings-app">
      <div className="settings-sidebar">
        {/* Uncategorized pages (General) */}
        {uncategorized.map(page => (
          <div
            key={page.id}
            className={`settings-page-item ${selectedPageId === page.id ? 'selected' : ''}`}
            onClick={() => setSelectedPageId(page.id)}
          >
            <span className="settings-page-icon">{page.icon}</span>
            <span className="settings-page-name">{page.name}</span>
          </div>
        ))}

        {/* Categorized pages */}
        {Object.entries(categorized).map(([category, pages]) => (
          <div key={category} className="settings-category">
            <div className="settings-category-header">{category}</div>
            {pages.map(page => (
              <div
                key={page.id}
                className={`settings-page-item ${selectedPageId === page.id ? 'selected' : ''}`}
                onClick={() => setSelectedPageId(page.id)}
              >
                <span className="settings-page-icon">{page.icon}</span>
                <span className="settings-page-name">{page.name}</span>
              </div>
            ))}
          </div>
        ))}
      </div>

      <div className="settings-content">
        {PageComponent && <PageComponent />}
      </div>
    </div>
  );
}
