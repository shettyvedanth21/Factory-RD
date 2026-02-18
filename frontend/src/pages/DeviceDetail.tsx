/**
 * Device Detail Page
 * Shows comprehensive device information, live KPIs, telemetry charts, and recent alerts.
 */
import { useParams, Link } from 'react-router-dom';
import { useDevice } from '../hooks/useDevices';
import { useAlerts } from '../hooks/useAlerts';
import KPICardGrid from '../components/kpi/KPICardGrid';
import TelemetryChart from '../components/charts/TelemetryChart';

// Helper to format relative time
function formatRelativeTime(dateString: string | null): string {
  if (!dateString) return 'Never';
  
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
  
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
}

// Helper to determine device status
function getDeviceStatus(lastSeen: string | null): { label: string; color: string } {
  if (!lastSeen) return { label: 'Offline', color: 'bg-red-100 text-red-800' };
  
  const lastSeenDate = new Date(lastSeen);
  const now = new Date();
  const diffMins = Math.floor((now.getTime() - lastSeenDate.getTime()) / 60000);
  
  if (diffMins < 10) {
    return { label: 'Online', color: 'bg-green-100 text-green-800' };
  }
  return { label: 'Offline', color: 'bg-red-100 text-red-800' };
}

// Helper to get severity badge color
function getSeverityColor(severity: string): string {
  switch (severity) {
    case 'critical':
      return 'bg-red-100 text-red-800';
    case 'high':
      return 'bg-orange-100 text-orange-800';
    case 'medium':
      return 'bg-yellow-100 text-yellow-800';
    case 'low':
      return 'bg-blue-100 text-blue-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
}

export default function DeviceDetail() {
  const { deviceId } = useParams<{ deviceId: string }>();
  const deviceIdNum = deviceId ? parseInt(deviceId, 10) : undefined;

  const { data: deviceData, isLoading, isError, error } = useDevice(deviceIdNum);
  const { data: alertsData } = useAlerts({ device_id: deviceIdNum, limit: 5 });

  const device = deviceData?.data;
  const recentAlerts = alertsData?.data || [];

  // Loading state
  if (isLoading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-gray-200 rounded w-1/3"></div>
          <div className="h-32 bg-gray-200 rounded"></div>
          <div className="grid grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-24 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (isError || !device) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <h2 className="text-xl font-bold text-red-800 mb-2">Device Not Found</h2>
          <p className="text-red-600 mb-4">
            {error instanceof Error ? error.message : 'The requested device could not be loaded.'}
          </p>
          <Link
            to="/machines"
            className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
          >
            ← Back to Machines
          </Link>
        </div>
      </div>
    );
  }

  const status = getDeviceStatus(device.last_seen);

  return (
    <div className="p-6">
      {/* Breadcrumb */}
      <nav className="mb-4 flex items-center text-sm text-gray-500">
        <Link to="/machines" className="hover:text-gray-700">
          Machines
        </Link>
        <span className="mx-2">/</span>
        <span className="text-gray-900 font-medium">{device.name || device.device_key}</span>
      </nav>

      {/* Device Header */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold text-gray-900">
                {device.name || device.device_key}
              </h1>
              <span
                className={`px-3 py-1 text-sm font-medium rounded-full ${status.color}`}
              >
                {status.label}
              </span>
            </div>
            
            <div className="flex flex-wrap gap-4 text-sm text-gray-600 mb-4">
              <div className="flex items-center gap-1">
                <span className="font-medium">Device Key:</span>
                <code className="px-2 py-1 bg-gray-100 rounded">{device.device_key}</code>
              </div>
              {device.region && (
                <div className="flex items-center gap-1">
                  <span className="font-medium">Region:</span>
                  <span>{device.region}</span>
                </div>
              )}
              {device.manufacturer && (
                <div className="flex items-center gap-1">
                  <span className="font-medium">Manufacturer:</span>
                  <span>{device.manufacturer}</span>
                </div>
              )}
              {device.model && (
                <div className="flex items-center gap-1">
                  <span className="font-medium">Model:</span>
                  <span>{device.model}</span>
                </div>
              )}
            </div>

            <div className="text-sm text-gray-500">
              Last seen: {formatRelativeTime(device.last_seen)}
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex gap-2">
            <button
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              onClick={() => alert('Edit functionality coming soon')}
            >
              Edit Device
            </button>
          </div>
        </div>
      </div>

      {/* KPI Cards Section */}
      <div className="mb-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Live Metrics</h2>
        <KPICardGrid deviceId={device.id} />
      </div>

      {/* Telemetry Chart Section */}
      <div className="mb-6">
        <TelemetryChart deviceId={device.id} parameters={device.parameters || []} />
      </div>

      {/* Recent Alerts Section */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-900">Recent Alerts</h2>
          <Link
            to={`/machines/${device.id}/alerts`}
            className="text-sm text-blue-600 hover:text-blue-700 font-medium"
          >
            View All →
          </Link>
        </div>

        {recentAlerts.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-6 text-center">
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
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <p className="mt-2 text-gray-600">No recent alerts</p>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow divide-y">
            {recentAlerts.map((alert) => (
              <div key={alert.id} className="p-4 hover:bg-gray-50">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className={`px-2 py-1 text-xs font-medium rounded ${getSeverityColor(
                          alert.severity
                        )}`}
                      >
                        {alert.severity.toUpperCase()}
                      </span>
                      <span className="text-sm text-gray-500">
                        {formatRelativeTime(alert.triggered_at)}
                      </span>
                    </div>
                    <p className="text-sm text-gray-900">{alert.message}</p>
                    {alert.resolved_at && (
                      <p className="text-xs text-green-600 mt-1">
                        ✓ Resolved {formatRelativeTime(alert.resolved_at)}
                      </p>
                    )}
                  </div>
                  {!alert.resolved_at && (
                    <button
                      className="ml-4 px-3 py-1 text-xs font-medium text-blue-600 hover:text-blue-700"
                      onClick={() => alert('Resolve functionality coming soon')}
                    >
                      Resolve
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
