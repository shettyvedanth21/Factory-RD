/**
 * Analytics Page
 * Job list, creation, and results visualization.
 */
import { useState } from 'react';
import { useAnalyticsJobs, useCreateAnalyticsJob, useDeleteAnalyticsJob } from '../hooks/useAnalytics';
import { useDevices } from '../hooks/useDevices';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

// Status badge helper
function getStatusBadge(status: string) {
  const badges = {
    pending: 'bg-yellow-100 text-yellow-800',
    running: 'bg-blue-100 text-blue-800',
    complete: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
  };
  return badges[status as keyof typeof badges] || 'bg-gray-100 text-gray-800';
}

// Format relative time
function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

export default function Analytics() {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  const { data, isLoading, isError, error } = useAnalyticsJobs({ page, per_page: 20 });
  const createJobMutation = useCreateAnalyticsJob();
  const deleteJobMutation = useDeleteAnalyticsJob();

  const jobs = data?.data || [];
  const pagination = data?.pagination;

  // Form state for create modal
  const [formData, setFormData] = useState({
    mode: 'standard' as 'standard' | 'ai_copilot',
    job_type: 'anomaly',
    device_ids: [] as number[],
    date_range_start: '',
    date_range_end: '',
  });

  const { data: devicesData } = useDevices({ per_page: 100 });
  const devices = devicesData?.data || [];

  // Handle create job
  const handleCreateJob = async () => {
    try {
      await createJobMutation.mutateAsync({
        job_type: formData.mode === 'ai_copilot' ? 'ai_copilot' : formData.job_type,
        device_ids: formData.device_ids,
        date_range_start: new Date(formData.date_range_start).toISOString(),
        date_range_end: new Date(formData.date_range_end).toISOString(),
        mode: formData.mode,
      });
      setShowCreateModal(false);
      // Reset form
      setFormData({
        mode: 'standard',
        job_type: 'anomaly',
        device_ids: [],
        date_range_start: '',
        date_range_end: '',
      });
    } catch (err) {
      console.error('Failed to create job:', err);
    }
  };

  // Handle delete job
  const handleDeleteJob = async (jobId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to cancel this job?')) return;
    
    try {
      await deleteJobMutation.mutateAsync(jobId);
    } catch (err) {
      console.error('Failed to delete job:', err);
    }
  };

  // Fetch results for expanded job
  const expandedJob = jobs.find((j: any) => j.id === expandedJobId);
  const [results, setResults] = useState<any>(null);

  // Fetch results when job is expanded and complete
  const fetchResults = async (url: string) => {
    try {
      const response = await fetch(url);
      const data = await response.json();
      setResults(data);
    } catch (err) {
      console.error('Failed to fetch results:', err);
    }
  };

  // Load results when job is expanded
  if (expandedJob && expandedJob.status === 'complete' && expandedJob.result_url && !results) {
    fetchResults(expandedJob.result_url);
  }

  // Clear results when job is collapsed
  if (!expandedJob && results) {
    setResults(null);
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Analytics</h1>
            <p className="mt-2 text-gray-600">
              Run ML-powered analysis on your factory data
            </p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700"
          >
            + New Analysis
          </button>
        </div>
      </div>

      {/* Error State */}
      {isError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800 font-medium">Failed to load analytics jobs</p>
          <p className="text-red-600 text-sm mt-1">
            {error instanceof Error ? error.message : 'Unknown error'}
          </p>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="animate-pulse space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-16 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      )}

      {/* Jobs Table */}
      {!isLoading && !isError && (
        <>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Devices</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date Range</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {jobs.map((job: any) => (
                  <>
                    <tr
                      key={job.id}
                      onClick={() => setExpandedJobId(expandedJobId === job.id ? null : job.id)}
                      className="hover:bg-gray-50 cursor-pointer"
                    >
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">{job.job_type}</div>
                        <div className="text-xs text-gray-500">{job.mode}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {job.device_ids.length} device{job.device_ids.length !== 1 ? 's' : ''}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(job.date_range_start).toLocaleDateString()} - {new Date(job.date_range_end).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs font-medium rounded ${getStatusBadge(job.status)}`}>
                          {job.status.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatRelativeTime(job.created_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                        {job.status === 'pending' && (
                          <button
                            onClick={(e) => handleDeleteJob(job.id, e)}
                            className="text-red-600 hover:text-red-900"
                          >
                            Cancel
                          </button>
                        )}
                        {job.status === 'complete' && (
                          <a
                            href={job.result_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="text-blue-600 hover:text-blue-900"
                          >
                            Download
                          </a>
                        )}
                      </td>
                    </tr>
                    {/* Expanded Results Panel */}
                    {expandedJobId === job.id && job.status === 'complete' && results && (
                      <tr>
                        <td colSpan={6} className="px-6 py-4 bg-gray-50">
                          <div className="space-y-4">
                            <h3 className="text-lg font-semibold text-gray-900">Results</h3>
                            
                            {/* Summary */}
                            <div className="bg-blue-50 border border-blue-200 rounded p-3">
                              <p className="text-sm text-blue-900">{results.summary}</p>
                            </div>

                            {/* Anomaly Detection Results */}
                            {results.anomaly_count !== undefined && (
                              <div>
                                <h4 className="font-medium text-gray-900 mb-2">Anomaly Detection</h4>
                                <div className="grid grid-cols-3 gap-4 mb-3">
                                  <div className="bg-white p-3 rounded border">
                                    <div className="text-xs text-gray-500">Anomalies Found</div>
                                    <div className="text-2xl font-bold text-red-600">{results.anomaly_count}</div>
                                  </div>
                                  <div className="bg-white p-3 rounded border">
                                    <div className="text-xs text-gray-500">Anomaly Score</div>
                                    <div className="text-2xl font-bold text-orange-600">{(results.anomaly_score * 100).toFixed(1)}%</div>
                                  </div>
                                  <div className="bg-white p-3 rounded border">
                                    <div className="text-xs text-gray-500">Total Data Points</div>
                                    <div className="text-2xl font-bold text-gray-900">{results.total_data_points}</div>
                                  </div>
                                </div>
                                
                                {results.anomalies && results.anomalies.length > 0 && (
                                  <div className="bg-white border rounded max-h-64 overflow-y-auto">
                                    <table className="min-w-full text-sm">
                                      <thead className="bg-gray-100 sticky top-0">
                                        <tr>
                                          <th className="px-3 py-2 text-left">Device</th>
                                          <th className="px-3 py-2 text-left">Timestamp</th>
                                          <th className="px-3 py-2 text-left">Score</th>
                                        </tr>
                                      </thead>
                                      <tbody className="divide-y">
                                        {results.anomalies.slice(0, 10).map((anomaly: any, idx: number) => (
                                          <tr key={idx}>
                                            <td className="px-3 py-2">{anomaly.device_id}</td>
                                            <td className="px-3 py-2">{new Date(anomaly.timestamp).toLocaleString()}</td>
                                            <td className="px-3 py-2 font-mono">{anomaly.score.toFixed(3)}</td>
                                          </tr>
                                        ))}
                                      </tbody>
                                    </table>
                                  </div>
                                )}
                              </div>
                            )}

                            {/* Forecast Results */}
                            {results.forecast && results.forecast.length > 0 && (
                              <div>
                                <h4 className="font-medium text-gray-900 mb-2">Energy Forecast</h4>
                                <div className="bg-white border rounded p-4" style={{ height: '300px' }}>
                                  <ResponsiveContainer width="100%" height="100%">
                                    <AreaChart data={results.forecast}>
                                      <CartesianGrid strokeDasharray="3 3" />
                                      <XAxis 
                                        dataKey="timestamp" 
                                        tickFormatter={(ts) => new Date(ts).toLocaleDateString()}
                                      />
                                      <YAxis />
                                      <Tooltip 
                                        labelFormatter={(ts) => new Date(ts).toLocaleString()}
                                        formatter={(value: number) => [value.toFixed(2), 'Power']}
                                      />
                                      <Area type="monotone" dataKey="yhat_lower" fill="#dbeafe" stroke="none" />
                                      <Area type="monotone" dataKey="yhat_upper" fill="#dbeafe" stroke="none" />
                                      <Area type="monotone" dataKey="yhat" fill="#3b82f6" stroke="#2563eb" />
                                    </AreaChart>
                                  </ResponsiveContainer>
                                </div>
                              </div>
                            )}

                            {/* Failure Prediction Results */}
                            {results.failure_probability !== undefined && (
                              <div>
                                <h4 className="font-medium text-gray-900 mb-2">Failure Prediction</h4>
                                <div className="grid grid-cols-2 gap-4">
                                  <div className="bg-white p-4 rounded border">
                                    <div className="text-sm text-gray-500 mb-1">Failure Probability</div>
                                    <div className="text-3xl font-bold text-orange-600">{(results.failure_probability * 100).toFixed(1)}%</div>
                                  </div>
                                  <div className="bg-white p-4 rounded border">
                                    <div className="text-sm text-gray-500 mb-1">Risk Level</div>
                                    <div className={`text-3xl font-bold ${
                                      results.risk_level === 'high' ? 'text-red-600' :
                                      results.risk_level === 'medium' ? 'text-yellow-600' : 'text-green-600'
                                    }`}>
                                      {results.risk_level.toUpperCase()}
                                    </div>
                                  </div>
                                </div>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {pagination && pagination.pages > 1 && (
            <div className="mt-4 flex justify-between items-center">
              <div className="text-sm text-gray-700">
                Page {page} of {pagination.pages}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(page - 1)}
                  disabled={page === 1}
                  className="px-3 py-1 border rounded disabled:opacity-50"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage(page + 1)}
                  disabled={page === pagination.pages}
                  className="px-3 py-1 border rounded disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Create Job Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">New Analysis</h2>
            
            <div className="space-y-4">
              {/* Mode Selector */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Mode</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => setFormData({ ...formData, mode: 'standard' })}
                    className={`p-3 border-2 rounded-lg text-left ${
                      formData.mode === 'standard' ? 'border-blue-600 bg-blue-50' : 'border-gray-300'
                    }`}
                  >
                    <div className="font-medium">Standard</div>
                    <div className="text-xs text-gray-600">Choose specific analysis type</div>
                  </button>
                  <button
                    onClick={() => setFormData({ ...formData, mode: 'ai_copilot' })}
                    className={`p-3 border-2 rounded-lg text-left ${
                      formData.mode === 'ai_copilot' ? 'border-purple-600 bg-purple-50' : 'border-gray-300'
                    }`}
                  >
                    <div className="font-medium">AI Co-Pilot</div>
                    <div className="text-xs text-gray-600">Run all analyses</div>
                  </button>
                </div>
              </div>

              {/* Analysis Type (only for standard mode) */}
              {formData.mode === 'standard' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Analysis Type</label>
                  <select
                    value={formData.job_type}
                    onChange={(e) => setFormData({ ...formData, job_type: e.target.value })}
                    className="w-full px-3 py-2 border rounded-md"
                  >
                    <option value="anomaly">Anomaly Detection</option>
                    <option value="energy_forecast">Energy Forecast</option>
                    <option value="failure_prediction">Failure Prediction</option>
                  </select>
                </div>
              )}

              {/* Device Selector */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Select Devices ({formData.device_ids.length} selected)
                </label>
                <div className="border rounded-md max-h-48 overflow-y-auto">
                  {devices.map((device: any) => (
                    <label key={device.id} className="flex items-center p-2 hover:bg-gray-50 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData.device_ids.includes(device.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setFormData({ ...formData, device_ids: [...formData.device_ids, device.id] });
                          } else {
                            setFormData({ ...formData, device_ids: formData.device_ids.filter(id => id !== device.id) });
                          }
                        }}
                        className="mr-2"
                      />
                      <span className="text-sm">{device.name || device.device_key}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Date Range */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Start Date</label>
                  <input
                    type="datetime-local"
                    value={formData.date_range_start}
                    onChange={(e) => setFormData({ ...formData, date_range_start: e.target.value })}
                    className="w-full px-3 py-2 border rounded-md"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">End Date</label>
                  <input
                    type="datetime-local"
                    value={formData.date_range_end}
                    onChange={(e) => setFormData({ ...formData, date_range_end: e.target.value })}
                    className="w-full px-3 py-2 border rounded-md"
                  />
                </div>
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-2">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 border rounded-md text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateJob}
                disabled={formData.device_ids.length === 0 || !formData.date_range_start || !formData.date_range_end}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
              >
                Create Job
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
