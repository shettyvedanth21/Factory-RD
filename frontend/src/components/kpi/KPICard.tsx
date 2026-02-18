/**
 * KPI Card Component
 * Displays a single KPI metric with value, unit, and stale state handling.
 */
import { useMemo } from 'react';

interface KPICardProps {
  parameter_key: string;
  display_name: string;
  unit: string;
  value: number | null;
  is_stale: boolean;
  className?: string;
}

export default function KPICard({
  parameter_key,
  display_name,
  unit,
  value,
  is_stale,
  className = '',
}: KPICardProps) {
  // Format value based on magnitude (0 decimals for large values, 2 for small)
  const formattedValue = useMemo(() => {
    if (value === null) return '—';
    
    // Use 0 decimals for values >= 100, otherwise 2 decimals
    const decimals = Math.abs(value) >= 100 ? 0 : 2;
    return value.toFixed(decimals);
  }, [value]);

  return (
    <div
      className={`
        bg-white rounded-lg shadow-sm border-t-4 border-blue-500 p-4 
        transition-all duration-300 hover:shadow-md
        ${is_stale ? 'opacity-50 bg-gray-50' : ''}
        ${className}
      `}
    >
      {/* Parameter Name */}
      <div className="text-sm font-medium text-gray-600 mb-2 truncate">
        {display_name}
      </div>

      {/* Value Display */}
      {is_stale ? (
        <div className="text-2xl font-bold text-gray-400">
          No data
        </div>
      ) : (
        <div className="flex items-baseline gap-2">
          <div className="text-3xl font-bold text-gray-900 transition-all duration-500">
            {formattedValue}
          </div>
          <div className="text-sm font-medium text-gray-500">
            {unit}
          </div>
        </div>
      )}

      {/* Optional: Parameter Key (for debugging) */}
      {process.env.NODE_ENV === 'development' && (
        <div className="text-xs text-gray-400 mt-1 truncate">
          {parameter_key}
        </div>
      )}
    </div>
  );
}
