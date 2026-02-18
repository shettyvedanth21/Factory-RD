/**
 * Dashboard page - main landing page after login.
 */
import { useDashboardSummary } from '../hooks/useDashboard';
import { useAuthStore } from '../stores/authStore';

// Skeleton loader for summary cards
function SummaryCardSkeleton() {
  return (
    <div className="bg-white rounded-lg shadow p-6 animate-pulse">
      <div className="h-4 bg-gray-200 rounded w-1/2 mb-3"></div>
      <div className="h-8 bg-gray-200 rounded w-3/4"></div>
    </div>
  );
}

// Helper to get health score badge color
function getHealthScoreColor(score: number): string {
  if (score >= 80) return 'bg-green-100 text-green-800';
  if (score >= 60) return 'bg-yellow-100 text-yellow-800';
  return 'bg-red-100 text-red-800';
}

export default function DashboardPage() {
  const user = useAuthStore((state) => state.user);
  const { data, isLoading, isError, error, dataUpdatedAt } = useDashboardSummary();

  const summary = data?.data;

  // Format last updated time
  const lastUpdated = new Date(dataUpdatedAt).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
            <p className="mt-2 text-gray-600">
              Welcome back, {user?.email}
            </p>
          </div>
          {!isLoading && !isError && (
            <div className="text-sm text-gray-500">
              Last updated: {lastUpdated}
            </div>
          )}
        </div>
      </div>

      {/* Error State */}
      {isError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800 font-medium">Failed to load dashboard data</p>
          <p className="text-red-600 text-sm mt-1">
            {error instanceof Error ? error.message : 'Unknown error'}
          </p>
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        {/* Total Machines */}
        {isLoading ? (
          <SummaryCardSkeleton />
        ) : (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500">Total Machines</h3>
            <p className="mt-2 text-3xl font-bold text-gray-900">
              {summary?.total_devices ?? '—'}
            </p>
          </div>
        )}

        {/* Active Machines */}
        {isLoading ? (
          <SummaryCardSkeleton />
        ) : (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500">Active</h3>
            <p className="mt-2 text-3xl font-bold text-green-600">
              {summary?.active_devices ?? '—'}
            </p>
            <p className="mt-1 text-xs text-gray-500">Online in last 10 min</p>
          </div>
        )}

        {/* Offline Machines */}
        {isLoading ? (
          <SummaryCardSkeleton />
        ) : (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500">Offline</h3>
            <p className="mt-2 text-3xl font-bold text-red-600">
              {summary?.offline_devices ?? '—'}
            </p>
          </div>
        )}

        {/* Active Alerts */}
        {isLoading ? (
          <SummaryCardSkeleton />
        ) : (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500">Active Alerts</h3>
            <p className="mt-2 text-3xl font-bold text-orange-600">
              {summary?.active_alerts ?? '—'}
            </p>
            {summary && summary.critical_alerts > 0 && (
              <p className="mt-1 text-xs text-red-600 font-medium">
                {summary.critical_alerts} critical
              </p>
            )}
          </div>
        )}
      </div>

      {/* Secondary Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        {/* Health Score */}
        {isLoading ? (
          <SummaryCardSkeleton />
        ) : (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500">Health Score</h3>
            <div className="mt-2 flex items-baseline gap-3">
              <p className="text-3xl font-bold text-gray-900">
                {summary?.health_score ?? '—'}
              </p>
              {summary && (
                <span
                  className={`px-2 py-1 text-sm font-medium rounded ${getHealthScoreColor(
                    summary.health_score
                  )}`}
                >
                  {summary.health_score >= 80
                    ? 'Good'
                    : summary.health_score >= 60
                    ? 'Fair'
                    : 'Poor'}
                </span>
              )}
            </div>
          </div>
        )}

        {/* Current Energy */}
        {isLoading ? (
          <SummaryCardSkeleton />
        ) : (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500">Current Energy</h3>
            <div className="mt-2 flex items-baseline gap-2">
              <p className="text-3xl font-bold text-gray-900">
                {summary?.current_energy_kw?.toFixed(2) ?? '—'}
              </p>
              <span className="text-sm text-gray-500">kW</span>
            </div>
          </div>
        )}

        {/* Energy Today */}
        {isLoading ? (
          <SummaryCardSkeleton />
        ) : (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500">Energy Today</h3>
            <div className="mt-2 flex items-baseline gap-2">
              <p className="text-3xl font-bold text-gray-900">
                {summary?.energy_today_kwh?.toFixed(2) ?? '—'}
              </p>
              <span className="text-sm text-gray-500">kWh</span>
            </div>
          </div>
        )}

        {/* Energy This Month */}
        {isLoading ? (
          <SummaryCardSkeleton />
        ) : (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500">Energy This Month</h3>
            <div className="mt-2 flex items-baseline gap-2">
              <p className="text-3xl font-bold text-gray-900">
                {summary?.energy_this_month_kwh?.toFixed(2) ?? '—'}
              </p>
              <span className="text-sm text-gray-500">kWh</span>
            </div>
          </div>
        )}
      </div>

      {/* Info Banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-blue-800">
          <strong>Live Dashboard:</strong> Data refreshes every 30 seconds. Navigate to{' '}
          <a href="/machines" className="underline font-medium">
            Machines
          </a>{' '}
          to view individual device metrics and telemetry charts.
        </p>
      </div>
    </div>
  );
}
