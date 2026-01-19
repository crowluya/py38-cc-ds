import React, { useState } from 'react';

interface DurationSelectorProps {
  value: number;
  onChange: (duration: number) => void;
  disabled?: boolean;
  presets?: { label: string; value: number }[];
}

const defaultPresets = [
  { label: '15 min', value: 900 },
  { label: '25 min', value: 1500 },
  { label: '45 min', value: 2700 },
  { label: '60 min', value: 3600 },
  { label: '90 min', value: 5400 },
];

export function DurationSelector({
  value,
  onChange,
  disabled = false,
  presets = defaultPresets,
}: DurationSelectorProps) {
  const [customValue, setCustomValue] = useState<string>('');
  const [showCustom, setShowCustom] = useState(false);

  const handleCustomChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setCustomValue(e.target.value);
    const minutes = parseInt(e.target.value, 10);
    if (!isNaN(minutes) && minutes > 0 && minutes <= 180) {
      onChange(minutes * 60);
    }
  };

  return (
    <div className="flex flex-col items-center gap-4">
      {/* Preset Buttons */}
      <div className="flex flex-wrap gap-2 justify-center">
        {presets.map((preset) => (
          <button
            key={preset.value}
            onClick={() => onChange(preset.value)}
            disabled={disabled}
            className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
              value === preset.value
                ? 'bg-blue-500 text-white shadow-lg scale-105'
                : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {preset.label}
          </button>
        ))}

        <button
          onClick={() => setShowCustom(!showCustom)}
          disabled={disabled}
          className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
            showCustom
              ? 'bg-purple-500 text-white shadow-lg scale-105'
              : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
          } disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          Custom
        </button>
      </div>

      {/* Custom Input */}
      {showCustom && (
        <div className="flex items-center gap-2">
          <input
            type="number"
            value={customValue}
            onChange={handleCustomChange}
            placeholder="Min"
            min="1"
            max="180"
            disabled={disabled}
            className="w-24 px-3 py-2 text-center border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          />
          <span className="text-gray-600 dark:text-gray-400">minutes</span>
        </div>
      )}
    </div>
  );
}
