/**
 * Dashboard page - main landing page after login.
 */
import { useDashboardSummary } from '../hooks/useDashboard';

export default function DashboardPage() {
  const { data: summary, isLoading } = useDashboardSummary();

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-32 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Health Score */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Health Score</h3>
          <p className="text-3xl font-bold text-gray-900">{summary?.health_score || 0}</p>
        </div>

        {/* Total Devices */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Total Devices</h3>
          <p className="text-3xl font-bold text-gray-900">{summary?.total_devices || 0}</p>
          <p className="text-sm text-gray-600 mt-1">
            {summary?.active_devices || 0} active, {summary?.offline_devices || 0} offline
          </p>
        </div>

        {/* Active Alerts */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Active Alerts</h3>
          <p className="text-3xl font-bold text-gray-900">{summary?.active_alerts || 0}</p>
          <p className="text-sm text-red-600 mt-1">
            {summary?.critical_alerts || 0} critical
          </p>
        </div>

        {/* Current Energy */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Current Energy</h3>
          <p className="text-3xl font-bold text-gray-900">
            {summary?.current_energy_kw.toFixed(1) || 0} kW
          </p>
        </div>
      </div>

      {/* Energy Summary */}
      <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Energy Today</h3>
          <p className="text-2xl font-bold text-gray-900">
            {summary?.energy_today_kwh.toFixed(2) || 0} kWh
          </p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Energy This Month</h3>
          <p className="text-2xl font-bold text-gray-900">
            {summary?.energy_this_month_kwh.toFixed(2) || 0} kWh
          </p>
        </div>
      </div>
    </div>
  );
}
