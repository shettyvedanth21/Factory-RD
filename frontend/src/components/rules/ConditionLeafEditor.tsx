/**
 * Condition Leaf Editor
 * Edits a single condition (parameter, operator, value).
 */
import type { ConditionLeaf, DeviceParameter } from '../../types';

interface ConditionLeafEditorProps {
  condition: ConditionLeaf;
  parameters: DeviceParameter[];
  onChange: (condition: ConditionLeaf) => void;
  onRemove: () => void;
}

// Human-readable operator labels
const OPERATOR_LABELS: Record<ConditionLeaf['operator'], string> = {
  gt: 'is greater than',
  lt: 'is less than',
  gte: 'is greater than or equal to',
  lte: 'is less than or equal to',
  eq: 'is equal to',
  neq: 'is not equal to',
};

export default function ConditionLeafEditor({
  condition,
  parameters,
  onChange,
  onRemove,
}: ConditionLeafEditorProps) {
  return (
    <div className="flex items-center gap-2 p-3 bg-gray-50 rounded-md border border-gray-200">
      {/* Parameter Dropdown */}
      <select
        value={condition.parameter}
        onChange={(e) => onChange({ ...condition, parameter: e.target.value })}
        className="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
      >
        <option value="">Select parameter...</option>
        {parameters.map((param) => (
          <option key={param.parameter_key} value={param.parameter_key}>
            {param.display_name || param.parameter_key} ({param.unit})
          </option>
        ))}
      </select>

      {/* Operator Dropdown */}
      <select
        value={condition.operator}
        onChange={(e) => onChange({ ...condition, operator: e.target.value as ConditionLeaf['operator'] })}
        className="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
      >
        {Object.entries(OPERATOR_LABELS).map(([op, label]) => (
          <option key={op} value={op}>
            {label}
          </option>
        ))}
      </select>

      {/* Value Input */}
      <input
        type="number"
        step="any"
        value={condition.value}
        onChange={(e) => onChange({ ...condition, value: parseFloat(e.target.value) || 0 })}
        placeholder="Value"
        className="w-32 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
      />

      {/* Remove Button */}
      <button
        onClick={onRemove}
        className="p-2 text-red-600 hover:text-red-800 hover:bg-red-50 rounded-md transition-colors"
        title="Remove condition"
      >
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}
