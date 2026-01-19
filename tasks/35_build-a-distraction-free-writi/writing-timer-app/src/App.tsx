import React, { useState, useEffect } from 'react';
import { TimerContainer } from './components/timer/TimerContainer';
import { WritingArea } from './components/writing/WritingArea';
import { StatisticsDashboard } from './components/statistics/StatisticsDashboard';
import { SettingsPanel } from './components/settings/SettingsPanel';
import { initializeDatabase } from './db/dexie';
import { db } from './db/dexie';
import type { Settings } from './types';

type View = 'timer' | 'writing' | 'statistics' | 'settings';

function App() {
  const [currentView, setCurrentView] = useState<View>('timer');
  const [settings, setSettings] = useState<Settings | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    const init = async () => {
      await initializeDatabase();
      const savedSettings = await db.settings.get(1);
      setSettings(savedSettings || null);
      setIsInitialized(true);
    };
    init();
  }, []);

  if (!isInitialized) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-100 dark:bg-gray-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`min-h-screen ${getThemeClass(settings?.theme || 'sepia')}`}>
      {/* Navigation */}
      <nav className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-gray-800 dark:text-white">
                ✍️ Writing Timer
              </h1>
            </div>

            <div className="flex items-center space-x-1">
              <NavButton
                view="timer"
                currentView={currentView}
                onClick={() => setCurrentView('timer')}
                label="Timer"
              />
              <NavButton
                view="writing"
                currentView={currentView}
                onClick={() => setCurrentView('writing')}
                label="Writing"
              />
              <NavButton
                view="statistics"
                currentView={currentView}
                onClick={() => setCurrentView('statistics')}
                label="Statistics"
              />
              <NavButton
                view="settings"
                currentView={currentView}
                onClick={() => setCurrentView('settings')}
                label="Settings"
              />
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {currentView === 'timer' && <TimerContainer />}

        {currentView === 'writing' && (
          <div className="h-[calc(100vh-200px)]">
            <WritingArea
              autoSaveInterval={settings?.autoSaveInterval || 30000}
              showWordCount={settings?.showWordCount || false}
              fontSize={settings?.fontSize || 'medium'}
              fontFamily={settings?.fontFamily || 'serif'}
              onSave={async (content) => {
                const words = content.trim().split(/\s+/).filter(w => w.length > 0).length;
                await db.writingContent.add({
                  content,
                  wordCount: words,
                  characterCount: content.length,
                  savedAt: Date.now(),
                  createdAt: Date.now(),
                  updatedAt: Date.now(),
                });
              }}
            />
          </div>
        )}

        {currentView === 'statistics' && <StatisticsDashboard />}

        {currentView === 'settings' && <SettingsPanel />}
      </main>
    </div>
  );
}

function NavButton({
  view,
  currentView,
  onClick,
  label,
}: {
  view: View;
  currentView: View;
  onClick: () => void;
  label: string;
}) {
  const isActive = currentView === view;

  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 rounded-lg font-medium transition-all ${
        isActive
          ? 'bg-blue-500 text-white shadow-md'
          : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
      }`}
    >
      {label}
    </button>
  );
}

function getThemeClass(theme: string): string {
  switch (theme) {
    case 'dark':
      return 'bg-gray-900';
    case 'sepia':
      return 'bg-amber-50';
    default:
      return 'bg-gray-50';
  }
}

export default App;
