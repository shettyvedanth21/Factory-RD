/**
 * Telemetry Chart Component
 * Displays historical telemetry data with parameter and time range selection.
 */
import { useState, useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { useKPIHistory } from '../../hooks/useKPIs';
import type { DeviceParameter } from '../../types';

interface TelemetryChartProps {
  deviceId: number;
  parameters: DeviceParameter[];
}

type TimeRange = '1H' | '24H' | '7D' | '30D';
type Interval = 'auto' | '1m' | '5m' | '1h' | '1d';

const TIME_RANGES: Record<TimeRange, { label: string; hours: number }> = {
  '1H': { label: '1 Hour', hours: 1 },
  '24H': { label: '24 Hours', hours: 24 },
  '7D': { label: '7 Days', hours: 168 },
  '30D': { label: '30 Days', hours: 720 },
};

const INTERVALS: Record<Interval, string> = {
  auto: 'Auto',
  '1m': '1 Minute',
  '5m': '5 Minutes',
  '1h': '1 Hour',
  '1d': '1 Day',
};

// Helper to calculate start/end timestamps
function getTimeRangeTimestamps(range: TimeRange) {
  const end = new Date();
  const start = new Date(end.getTime() - TIME_RANGES[range].hours * 60 * 60 * 1000);
  
  return {
    start: start.toISOString(),
    end: end.toISOString(),
  };
}

// Helper to format timestamp based on time range
function formatTimestamp(timestamp: string, range: TimeRange): string {
  const date = new Date(timestamp);
  
  if (range === '1H') {
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  } else if (range === '24H') {
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  } else if (range === '7D') {
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit' });
  } else {
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }
}

// Helper to get auto interval based on time range
function getAutoInterval(range: TimeRange): string {
  switch (range) {
    case '1H':
      return '1m';
    case '24H':
      return '5m';
    case '7D':
      return '1h';
    case '30D':
      return '1d';
    default:
      return '5m';
  }
}

export default function TelemetryChart({ deviceId, parameters }: TelemetryChartProps) {
  // Filter to only show KPI-selected parameters
  const kpiParameters = useMemo(
    () => parameters.filter((p) => p.is_kpi_selected),
    [parameters]
  );

  const [selectedParameter, setSelectedParameter] = useState<string>(
    kpiParameters[0]?.parameter_key || ''
  );
  const [timeRange, setTimeRange] = useState<TimeRange>('24H');
  const [interval, setInterval] = useState<Interval>('auto');

  // Build query params
  const queryParams = useMemo(() => {
    if (!selectedParameter) return undefined;

    const { start, end } = getTimeRangeTimestamps(timeRange);
    const actualInterval = interval === 'auto' ? getAutoInterval(timeRange) : interval;

    return {
      parameter: selectedParameter,
      start,
      end,
      interval: actualInterval,
    };
  }, [selectedParameter, timeRange, interval]);

  const { data, isLoading, isError, error } = useKPIHistory(deviceId, queryParams);

  // Get current parameter details
  const currentParameter = useMemo(
    () => kpiParameters.find((p) => p.parameter_key === selectedParameter),
    [kpiParameters, selectedParameter]
  );

  // Empty state - no parameters
  if (kpiParameters.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Telemetry Chart</h3>
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
          <p className="text-gray-600">No KPI parameters available for charting.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      {/* Header */}
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Telemetry History</h3>

      {/* Controls */}
      <div className="flex flex-wrap gap-4 mb-6">
        {/* Parameter Selector */}
        <div className="flex-1 min-w-[200px]">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Parameter
          </label>
          <select
            value={selectedParameter}
            onChange={(e) => setSelectedParameter(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          >
            {kpiParameters.map((param) => (
              <option key={param.parameter_key} value={param.parameter_key}>
                {param.display_name} ({param.unit})
              </option>
            ))}
          </select>
        </div>

        {/* Time Range Buttons */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Time Range
          </label>
          <div className="flex gap-1">
            {(Object.keys(TIME_RANGES) as TimeRange[]).map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                  timeRange === range
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {range}
              </button>
            ))}
          </div>
        </div>

        {/* Interval Selector */}
        <div className="min-w-[140px]">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Interval
          </label>
          <select
            value={interval}
            onChange={(e) => setInterval(e.target.value as Interval)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          >
            {(Object.keys(INTERVALS) as Interval[]).map((int) => (
              <option key={int} value={int}>
                {INTERVALS[int]}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Chart Area */}
      <div className="relative" style={{ height: '400px' }}>
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-75 z-10">
            <div className="flex items-center gap-2">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <span className="text-gray-600">Loading data...</span>
            </div>
          </div>
        )}

        {isError && (
          <div className="flex items-center justify-center h-full">
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center max-w-md">
              <p className="text-red-800 font-medium">Failed to load chart data</p>
              <p className="text-red-600 text-sm mt-1">
                {error instanceof Error ? error.message : 'Unknown error'}
              </p>
            </div>
          </div>
        )}

        {!isLoading && !isError && data?.data && data.data.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 text-center">
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
              <p className="text-gray-600 mt-2">No data for selected range</p>
            </div>
          </div>
        )}

        {!isLoading && !isError && data?.data && data.data.length > 0 && (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={data.data}
              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="timestamp"
                tickFormatter={(value) => formatTimestamp(value, timeRange)}
                stroke="#6b7280"
                style={{ fontSize: '12px' }}
              />
              <YAxis
                label={{
                  value: currentParameter?.unit || '',
                  angle: -90,
                  position: 'insideLeft',
                  style: { fontSize: '12px', fill: '#6b7280' },
                }}
                stroke="#6b7280"
                style={{ fontSize: '12px' }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'white',
                  border: '1px solid #e5e7eb',
                  borderRadius: '6px',
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                }}
                labelFormatter={(value) => {
                  const date = new Date(value as string);
                  return date.toLocaleString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  });
                }}
                formatter={(value: number) => [
                  `${value.toFixed(2)} ${currentParameter?.unit || ''}`,
                  currentParameter?.display_name || 'Value',
                ]}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="#2563eb"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
