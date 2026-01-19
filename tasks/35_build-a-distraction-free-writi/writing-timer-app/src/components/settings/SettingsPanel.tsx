import React, { useState, useEffect } from 'react';
import { db } from '../../db/dexie';
import type { Settings, Theme, FontSize, FontFamily } from '../../types';

export function SettingsPanel() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [saveMessage, setSaveMessage] = useState('');

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    const savedSettings = await db.settings.get(1);
    setSettings(savedSettings || null);
  };

  const updateSetting = async (updates: Partial<Settings>) => {
    if (!settings) return;

    const updatedSettings = {
      ...settings,
      ...updates,
      updatedAt: Date.now(),
    };

    await db.settings.update(1, updatedSettings);
    setSettings(updatedSettings);
    setSaveMessage('Settings saved!');
    setTimeout(() => setSaveMessage(''), 2000);
  };

  if (!settings) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Save Message */}
      {saveMessage && (
        <div className="bg-green-100 dark:bg-green-900/20 text-green-800 dark:text-green-200 px-4 py-2 rounded-lg text-center">
          {saveMessage}
        </div>
      )}

      {/* Timer Settings */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6 border border-gray-200 dark:border-gray-700">
        <h2 className="text-xl font-bold text-gray-800 dark:text-gray-100 mb-4">
          ⏱️ Timer Settings
        </h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Default Focus Duration (minutes)
            </label>
            <select
              value={settings.defaultFocusDuration / 60}
              onChange={(e) => updateSetting({ defaultFocusDuration: parseInt(e.target.value) * 60 })}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value={15}>15 minutes</option>
              <option value={25}>25 minutes (Pomodoro)</option>
              <option value={45}>45 minutes</option>
              <option value={60}>60 minutes</option>
              <option value={90}>90 minutes</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Default Short Break (minutes)
            </label>
            <select
              value={settings.defaultShortBreak / 60}
              onChange={(e) => updateSetting({ defaultShortBreak: parseInt(e.target.value) * 60 })}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value={3}>3 minutes</option>
              <option value={5}>5 minutes</option>
              <option value={10}>10 minutes</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Default Long Break (minutes)
            </label>
            <select
              value={settings.defaultLongBreak / 60}
              onChange={(e) => updateSetting({ defaultLongBreak: parseInt(e.target.value) * 60 })}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value={10}>10 minutes</option>
              <option value={15}>15 minutes</option>
              <option value={20}>20 minutes</option>
              <option value={30}>30 minutes</option>
            </select>
          </div>

          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Auto-start breaks after focus sessions
            </label>
            <button
              onClick={() => updateSetting({ autoStartBreaks: !settings.autoStartBreaks })}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                settings.autoStartBreaks ? 'bg-blue-500' : 'bg-gray-300 dark:bg-gray-600'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  settings.autoStartBreaks ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Auto-start next focus session
            </label>
            <button
              onClick={() => updateSetting({ autoStartSessions: !settings.autoStartSessions })}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                settings.autoStartSessions ? 'bg-blue-500' : 'bg-gray-300 dark:bg-gray-600'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  settings.autoStartSessions ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
        </div>
      </div>

      {/* Notification Settings */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6 border border-gray-200 dark:border-gray-700">
        <h2 className="text-xl font-bold text-gray-800 dark:text-gray-100 mb-4">
          🔔 Notifications
        </h2>

        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Enable browser notifications
            </label>
            <button
              onClick={() => updateSetting({ enableNotifications: !settings.enableNotifications })}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                settings.enableNotifications ? 'bg-blue-500' : 'bg-gray-300 dark:bg-gray-600'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  settings.enableNotifications ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Enable sound alerts
            </label>
            <button
              onClick={() => updateSetting({ enableSound: !settings.enableSound })}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                settings.enableSound ? 'bg-blue-500' : 'bg-gray-300 dark:bg-gray-600'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  settings.enableSound ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {settings.enableSound && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Sound Volume ({Math.round(settings.soundVolume * 100)}%)
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={settings.soundVolume}
                onChange={(e) => updateSetting({ soundVolume: parseFloat(e.target.value) })}
                className="w-full"
              />
            </div>
          )}
        </div>
      </div>

      {/* Appearance Settings */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6 border border-gray-200 dark:border-gray-700">
        <h2 className="text-xl font-bold text-gray-800 dark:text-gray-100 mb-4">
          🎨 Appearance
        </h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Theme
            </label>
            <div className="flex gap-2">
              {(['light', 'dark', 'sepia'] as Theme[]).map((theme) => (
                <button
                  key={theme}
                  onClick={() => updateSetting({ theme })}
                  className={`flex-1 px-4 py-2 rounded-lg font-medium capitalize transition-all ${
                    settings.theme === theme
                      ? 'bg-blue-500 text-white shadow-md'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                  }`}
                >
                  {theme}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Font Size
            </label>
            <select
              value={settings.fontSize}
              onChange={(e) => updateSetting({ fontSize: e.target.value as FontSize })}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="small">Small</option>
              <option value="medium">Medium</option>
              <option value="large">Large</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Font Family
            </label>
            <select
              value={settings.fontFamily}
              onChange={(e) => updateSetting({ fontFamily: e.target.value as FontFamily })}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="serif">Serif</option>
              <option value="sans">Sans-serif</option>
              <option value="mono">Monospace</option>
            </select>
          </div>
        </div>
      </div>

      {/* Writing Settings */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6 border border-gray-200 dark:border-gray-700">
        <h2 className="text-xl font-bold text-gray-800 dark:text-gray-100 mb-4">
          ✍️ Writing Settings
        </h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Auto-save interval (seconds)
            </label>
            <input
              type="number"
              min="10"
              max="300"
              value={settings.autoSaveInterval}
              onChange={(e) => updateSetting({ autoSaveInterval: parseInt(e.target.value) })}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Show word count while writing
            </label>
            <button
              onClick={() => updateSetting({ showWordCount: !settings.showWordCount })}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                settings.showWordCount ? 'bg-blue-500' : 'bg-gray-300 dark:bg-gray-600'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  settings.showWordCount ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
        </div>
      </div>

      {/* Goals */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6 border border-gray-200 dark:border-gray-700">
        <h2 className="text-xl font-bold text-gray-800 dark:text-gray-100 mb-4">
          🎯 Daily Goals
        </h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Daily writing goal (minutes)
            </label>
            <input
              type="number"
              min="10"
              max="480"
              value={settings.dailyGoalMinutes}
              onChange={(e) => updateSetting({ dailyGoalMinutes: parseInt(e.target.value) })}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Daily word count goal
            </label>
            <input
              type="number"
              min="100"
              max="10000"
              step="100"
              value={settings.dailyGoalWords}
              onChange={(e) => updateSetting({ dailyGoalWords: parseInt(e.target.value) })}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
