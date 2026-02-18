/**
 * Condition Group Editor
 * Edits a group of conditions with AND/OR logic, supports nesting up to depth 2.
 */
import type { ConditionTree, ConditionLeaf, DeviceParameter } from '../../types';
import ConditionLeafEditor from './ConditionLeafEditor';

interface ConditionGroupEditorProps {
  group: ConditionTree;
  parameters: DeviceParameter[];
  onChange: (group: ConditionTree) => void;
  onRemove?: () => void;
  depth?: number;
}

// Type guard to check if condition is a leaf
function isConditionLeaf(condition: ConditionLeaf | ConditionTree): condition is ConditionLeaf {
  return 'parameter' in condition;
}

export default function ConditionGroupEditor({
  group,
  parameters,
  onChange,
  onRemove,
  depth = 0,
}: ConditionGroupEditorProps) {
  // Handle operator toggle (AND/OR)
  const handleOperatorToggle = () => {
    onChange({
      ...group,
      operator: group.operator === 'AND' ? 'OR' : 'AND',
    });
  };

  // Add new leaf condition
  const handleAddCondition = () => {
    const newCondition: ConditionLeaf = {
      parameter: parameters[0]?.parameter_key || '',
      operator: 'gt',
      value: 0,
    };

    onChange({
      ...group,
      conditions: [...group.conditions, newCondition],
    });
  };

  // Add new nested group
  const handleAddGroup = () => {
    if (depth >= 2) return; // Max depth reached

    const newGroup: ConditionTree = {
      operator: 'AND',
      conditions: [
        {
          parameter: parameters[0]?.parameter_key || '',
          operator: 'gt',
          value: 0,
        },
      ],
    };

    onChange({
      ...group,
      conditions: [...group.conditions, newGroup],
    });
  };

  // Update a specific condition
  const handleUpdateCondition = (index: number, updatedCondition: ConditionLeaf | ConditionTree) => {
    const newConditions = [...group.conditions];
    newConditions[index] = updatedCondition;
    onChange({
      ...group,
      conditions: newConditions,
    });
  };

  // Remove a specific condition
  const handleRemoveCondition = (index: number) => {
    const newConditions = group.conditions.filter((_, i) => i !== index);
    
    // If no conditions left and this is a nested group, remove the group itself
    if (newConditions.length === 0 && onRemove) {
      onRemove();
    } else {
      onChange({
        ...group,
        conditions: newConditions,
      });
    }
  };

  // Calculate indentation based on depth
  const indentClass = depth === 0 ? '' : depth === 1 ? 'ml-4' : 'ml-8';
  const borderClass = depth === 0 ? 'border-2 border-blue-200' : 'border border-gray-300';

  return (
    <div className={`p-4 bg-white rounded-lg ${borderClass} ${indentClass}`}>
      {/* Header: Operator Toggle + Remove */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          {/* AND/OR Toggle */}
          <button
            onClick={handleOperatorToggle}
            className={`px-3 py-1 text-sm font-semibold rounded-md transition-colors ${
              group.operator === 'AND'
                ? 'bg-blue-600 text-white'
                : 'bg-purple-600 text-white'
            }`}
          >
            {group.operator}
          </button>
          <span className="text-sm text-gray-600">
            {group.operator === 'AND' ? 'All conditions must match' : 'Any condition can match'}
          </span>
        </div>

        {/* Remove Group Button (only for nested groups) */}
        {depth > 0 && onRemove && (
          <button
            onClick={onRemove}
            className="p-1 text-red-600 hover:text-red-800 hover:bg-red-50 rounded-md transition-colors"
            title="Remove group"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {/* Conditions List */}
      <div className="space-y-3 mb-4">
        {group.conditions.map((condition, index) => (
          <div key={index}>
            {isConditionLeaf(condition) ? (
              <ConditionLeafEditor
                condition={condition}
                parameters={parameters}
                onChange={(updated) => handleUpdateCondition(index, updated)}
                onRemove={() => handleRemoveCondition(index)}
              />
            ) : (
              <ConditionGroupEditor
                group={condition}
                parameters={parameters}
                onChange={(updated) => handleUpdateCondition(index, updated)}
                onRemove={() => handleRemoveCondition(index)}
                depth={depth + 1}
              />
            )}
          </div>
        ))}
      </div>

      {/* Add Buttons */}
      <div className="flex gap-2">
        <button
          onClick={handleAddCondition}
          className="px-3 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-md hover:bg-blue-100 transition-colors"
        >
          + Add Condition
        </button>

        {depth < 2 && (
          <button
            onClick={handleAddGroup}
            className="px-3 py-2 text-sm font-medium text-purple-600 bg-purple-50 rounded-md hover:bg-purple-100 transition-colors"
          >
            + Add Group
          </button>
        )}
      </div>
    </div>
  );
}
