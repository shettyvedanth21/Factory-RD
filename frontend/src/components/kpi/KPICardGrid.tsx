/**
 * KPI Card Grid Component
 * Displays live KPI values for a device in a responsive grid.
 */
import { Link } from 'react-router-dom';
import { useKPIsLive } from '../../hooks/useKPIs';
import KPICard from './KPICard';

interface KPICardGridProps {
  deviceId: number;
}

// Skeleton loader for KPI cards
function KPICardSkeleton() {
  return (
    <div className="bg-white rounded-lg shadow-sm border-t-4 border-gray-300 p-4 animate-pulse">
      <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
      <div className="h-8 bg-gray-200 rounded w-1/2"></div>
    </div>
  );
}

export default function KPICardGrid({ deviceId }: KPICardGridProps) {
  const { data, isLoading, isError, error } = useKPIsLive(deviceId);

  // Loading state
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {[...Array(8)].map((_, i) => (
          <KPICardSkeleton key={i} />
        ))}
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
        <p className="text-red-800 font-medium">Failed to load KPIs</p>
        <p className="text-red-600 text-sm mt-1">
          {error instanceof Error ? error.message : 'Unknown error'}
        </p>
      </div>
    );
  }

  const kpis = data?.data || [];

  // Empty state - no KPIs selected
  if (kpis.length === 0) {
    return (
      <div className="bg-gray-50 border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
        <svg
          className="mx-auto h-12 w-12 text-gray-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
          />
        </svg>
        <h3 className="mt-2 text-sm font-medium text-gray-900">No KPIs Selected</h3>
        <p className="mt-1 text-sm text-gray-500">
          Select parameters to display as KPIs in the device settings.
        </p>
        <div className="mt-4">
          <Link
            to={`/machines/${deviceId}/parameters`}
            className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
          >
            Manage Parameters
          </Link>
        </div>
      </div>
    );
  }

  // Render KPI cards
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      {kpis.map((kpi) => (
        <KPICard
          key={kpi.parameter_key}
          parameter_key={kpi.parameter_key}
          display_name={kpi.display_name}
          unit={kpi.unit}
          value={kpi.value}
          is_stale={kpi.is_stale}
        />
      ))}
    </div>
  );
}
