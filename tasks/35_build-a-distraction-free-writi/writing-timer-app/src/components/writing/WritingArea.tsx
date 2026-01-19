import React, { useState, useEffect, useRef } from 'react';

interface WritingAreaProps {
  onSave?: (content: string) => void;
  autoSaveInterval?: number;
  showWordCount?: boolean;
  fontSize?: 'small' | 'medium' | 'large';
  fontFamily?: 'serif' | 'sans' | 'mono';
  readOnly?: boolean;
}

export function WritingArea({
  onSave,
  autoSaveInterval = 30000,
  showWordCount = false,
  fontSize = 'medium',
  fontFamily = 'serif',
  readOnly = false,
}: WritingAreaProps) {
  const [content, setContent] = useState('');
  const [wordCount, setWordCount] = useState(0);
  const [characterCount, setCharacterCount] = useState(0);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const fontSizeClasses = {
    small: 'text-base',
    medium: 'text-lg',
    large: 'text-xl',
  };

  const fontFamilyClasses = {
    serif: 'font-serif',
    sans: 'font-sans',
    mono: 'font-mono',
  };

  // Calculate word and character count
  useEffect(() => {
    const words = content.trim().split(/\s+/).filter(word => word.length > 0);
    setWordCount(words.length);
    setCharacterCount(content.length);
  }, [content]);

  // Auto-save functionality
  useEffect(() => {
    if (!content || readOnly) return;

    const autoSaveTimer = setTimeout(() => {
      if (onSave) {
        onSave(content);
        setLastSaved(new Date());
      }
    }, autoSaveInterval);

    return () => clearTimeout(autoSaveTimer);
  }, [content, autoSaveInterval, onSave, readOnly]);

  // Handle fullscreen toggle
  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
    if (!isFullscreen) {
      document.documentElement.requestFullscreen?.();
    } else {
      document.exitFullscreen?.();
    }
  };

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      // Ctrl+S / Cmd+S to save
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        if (onSave && content) {
          onSave(content);
          setLastSaved(new Date());
        }
      }

      // F11 for fullscreen (prevent default and use custom handler)
      if (e.key === 'F11') {
        e.preventDefault();
        toggleFullscreen();
      }

      // Escape to exit fullscreen
      if (e.key === 'Escape' && isFullscreen) {
        setIsFullscreen(false);
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [content, onSave, isFullscreen]);

  const handleManualSave = () => {
    if (onSave && content) {
      onSave(content);
      setLastSaved(new Date());
    }
  };

  const handleClear = () => {
    if (window.confirm('Are you sure you want to clear all text? This cannot be undone.')) {
      setContent('');
      setWordCount(0);
      setCharacterCount(0);
    }
  };

  const handleExport = () => {
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `writing-${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div
      className={`flex flex-col h-full bg-white dark:bg-gray-900 transition-all ${
        isFullscreen ? 'fixed inset-0 z-50' : ''
      }`}
    >
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
        <div className="flex items-center gap-2">
          {showWordCount && (
            <div className="text-sm text-gray-600 dark:text-gray-400">
              <span className="font-semibold">{wordCount}</span> words
              <span className="mx-2">•</span>
              <span className="font-semibold">{characterCount}</span> characters
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          {lastSaved && (
            <span className="text-xs text-gray-500 dark:text-gray-400">
              Saved {lastSaved.toLocaleTimeString()}
            </span>
          )}

          <button
            onClick={handleManualSave}
            disabled={readOnly || !content}
            className="px-3 py-1 text-sm bg-blue-500 hover:bg-blue-600 text-white rounded disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="Save (Ctrl+S)"
          >
            Save
          </button>

          <button
            onClick={handleExport}
            disabled={!content}
            className="px-3 py-1 text-sm bg-gray-500 hover:bg-gray-600 text-white rounded disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="Export to file"
          >
            Export
          </button>

          <button
            onClick={handleClear}
            disabled={!content}
            className="px-3 py-1 text-sm bg-red-500 hover:bg-red-600 text-white rounded disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="Clear all text"
          >
            Clear
          </button>

          <button
            onClick={toggleFullscreen}
            className="px-3 py-1 text-sm bg-purple-500 hover:bg-purple-600 text-white rounded transition-colors"
            title="Toggle fullscreen (F11)"
          >
            {isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
          </button>
        </div>
      </div>

      {/* Writing Area */}
      <div className="flex-1 overflow-hidden">
        <textarea
          ref={textareaRef}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          readOnly={readOnly}
          placeholder="Start writing..."
          className={`w-full h-full p-8 resize-none outline-none bg-white dark:bg-gray-900 text-gray-800 dark:text-gray-100 ${fontSizeClasses[fontSize]} ${fontFamilyClasses[fontFamily]} leading-relaxed placeholder-gray-400 dark:placeholder-gray-600`}
        />
      </div>

      {/* Status Bar */}
      <div className="px-4 py-2 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-xs text-gray-500 dark:text-gray-400">
        <div className="flex justify-between">
          <span>Auto-save every {autoSaveInterval / 1000}s</span>
          <span>Press Ctrl+S to save • F11 for fullscreen</span>
        </div>
      </div>
    </div>
  );
}
