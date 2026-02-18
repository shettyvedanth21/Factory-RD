/**
 * Reports Page
 * Report list, creation, and download.
 */
import { useState } from 'react';
import { useReports, useCreateReport } from '../hooks/useReports';
import { useDevices } from '../hooks/useDevices';
import { useAnalyticsJobs } from '../hooks/useAnalytics';

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

// Format file size
function formatFileSize(bytes?: number): string {
  if (!bytes) return 'N/A';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
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

// Calculate time until expiration
function getExpiresIn(expiresAt?: string): string {
  if (!expiresAt) return 'Never';
  
  const expires = new Date(expiresAt);
  const now = new Date();
  const diffMs = expires.getTime() - now.getTime();
  
  if (diffMs < 0) return 'Expired';
  
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  if (diffHours < 1) {
    const diffMins = Math.floor(diffMs / (1000 * 60));
    return `${diffMins}m`;
  }
  return `${diffHours}h`;
}

export default function Reports() {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [page, setPage] = useState(1);

  const { data, isLoading, isError, error } = useReports({ page, per_page: 20 });
  const createReportMutation = useCreateReport();

  const reports = data?.data || [];
  const pagination = data?.pagination;

  // Form state for create modal
  const [formData, setFormData] = useState({
    title: '',
    device_ids: [] as number[],
    date_range_start: '',
    date_range_end: '',
    format: 'pdf',
    include_analytics: false,
    analytics_job_id: '',
  });

  const { data: devicesData } = useDevices({ per_page: 100 });
  const devices = devicesData?.data || [];

  const { data: analyticsJobsData } = useAnalyticsJobs({ status: 'complete', per_page: 50 });
  const analyticsJobs = analyticsJobsData?.data || [];

  // Handle create report
  const handleCreateReport = async () => {
    try {
      await createReportMutation.mutateAsync({
        title: formData.title || undefined,
        device_ids: formData.device_ids,
        date_range_start: new Date(formData.date_range_start).toISOString(),
        date_range_end: new Date(formData.date_range_end).toISOString(),
        format: formData.format,
        include_analytics: formData.include_analytics,
        analytics_job_id: formData.include_analytics ? formData.analytics_job_id : undefined,
      });
      setShowCreateModal(false);
      // Reset form
      setFormData({
        title: '',
        device_ids: [],
        date_range_start: '',
        date_range_end: '',
        format: 'pdf',
        include_analytics: false,
        analytics_job_id: '',
      });
    } catch (err) {
      console.error('Failed to create report:', err);
    }
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Reports</h1>
            <p className="mt-2 text-gray-600">
              Generate comprehensive reports in PDF, Excel, or JSON format
            </p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700"
          >
            + Generate Report
          </button>
        </div>
      </div>

      {/* Error State */}
      {isError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800 font-medium">Failed to load reports</p>
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

      {/* Reports Table */}
      {!isLoading && !isError && (
        <>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Title</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Format</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Devices</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date Range</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Size</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Expires</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {reports.map((report: any) => (
                  <tr key={report.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div className="text-sm font-medium text-gray-900">
                        {report.title || 'Factory Operations Report'}
                      </div>
                      {report.include_analytics && (
                        <div className="text-xs text-purple-600">Includes Analytics</div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded uppercase">
                        {report.format}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {report.device_ids.length} device{report.device_ids.length !== 1 ? 's' : ''}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(report.date_range_start).toLocaleDateString()} - {new Date(report.date_range_end).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs font-medium rounded ${getStatusBadge(report.status)}`}>
                        {report.status.toUpperCase()}
                      </span>
                      {report.error_message && (
                        <div className="text-xs text-red-600 mt-1" title={report.error_message}>
                          Error
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatFileSize(report.file_size_bytes)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {getExpiresIn(report.expires_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                      {report.status === 'complete' && report.file_url && (
                        <a
                          href={`/api/v1/reports/${report.id}/download`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:text-blue-900 font-medium"
                        >
                          Download
                        </a>
                      )}
                    </td>
                  </tr>
                ))}
                {reports.length === 0 && (
                  <tr>
                    <td colSpan={8} className="px-6 py-12 text-center">
                      <div className="text-gray-500">No reports generated yet</div>
                      <button
                        onClick={() => setShowCreateModal(true)}
                        className="mt-4 text-blue-600 hover:text-blue-700 font-medium"
                      >
                        Generate your first report
                      </button>
                    </td>
                  </tr>
                )}
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

      {/* Create Report Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Generate Report</h2>
            
            <div className="space-y-4">
              {/* Title */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Report Title (Optional)
                </label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="e.g., Monthly Operations Report"
                  className="w-full px-3 py-2 border rounded-md"
                />
              </div>

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

              {/* Format Selector */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Format</label>
                <div className="grid grid-cols-3 gap-2">
                  {['pdf', 'excel', 'json'].map((format) => (
                    <button
                      key={format}
                      onClick={() => setFormData({ ...formData, format })}
                      className={`p-3 border-2 rounded-lg ${
                        formData.format === format ? 'border-blue-600 bg-blue-50' : 'border-gray-300'
                      }`}
                    >
                      <div className="font-medium uppercase text-sm">{format}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Include Analytics */}
              <div>
                <label className="flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.include_analytics}
                    onChange={(e) => setFormData({ ...formData, include_analytics: e.target.checked })}
                    className="mr-2"
                  />
                  <span className="text-sm font-medium text-gray-700">Include Analytics Results</span>
                </label>
              </div>

              {/* Analytics Job Selector */}
              {formData.include_analytics && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Select Analytics Job
                  </label>
                  <select
                    value={formData.analytics_job_id}
                    onChange={(e) => setFormData({ ...formData, analytics_job_id: e.target.value })}
                    className="w-full px-3 py-2 border rounded-md"
                  >
                    <option value="">-- Select a completed analytics job --</option>
                    {analyticsJobs.map((job: any) => (
                      <option key={job.id} value={job.id}>
                        {job.job_type} - {new Date(job.created_at).toLocaleDateString()}
                      </option>
                    ))}
                  </select>
                  {analyticsJobs.length === 0 && (
                    <p className="text-xs text-gray-500 mt-1">
                      No completed analytics jobs available. Run an analysis first.
                    </p>
                  )}
                </div>
              )}
            </div>

            <div className="mt-6 flex justify-end gap-2">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 border rounded-md text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateReport}
                disabled={
                  formData.device_ids.length === 0 || 
                  !formData.date_range_start || 
                  !formData.date_range_end ||
                  (formData.include_analytics && !formData.analytics_job_id)
                }
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
              >
                Generate Report
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
