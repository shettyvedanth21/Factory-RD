/**
 * Machines List Page
 * Displays all devices with search, filtering, and pagination.
 */
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useDevices } from '../hooks/useDevices';

// Helper to get device status
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

// Helper to format relative time
function formatRelativeTime(dateString: string | null): string {
  if (!dateString) return 'Never';
  
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

// Device Card Component
interface DeviceCardProps {
  device: any;
}

function DeviceCard({ device }: DeviceCardProps) {
  const status = getDeviceStatus(device.last_seen);
  
  return (
    <Link
      to={`/machines/${device.id}`}
      className="block bg-white rounded-lg shadow hover:shadow-lg transition-shadow p-6"
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900 mb-1">
            {device.name || device.device_key}
          </h3>
          <code className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
            {device.device_key}
          </code>
        </div>
        <span className={`px-2 py-1 text-xs font-medium rounded ${status.color}`}>
          {status.label}
        </span>
      </div>

      {/* Metadata */}
      <div className="space-y-1 text-sm text-gray-600 mb-3">
        {device.region && (
          <div className="flex items-center gap-1">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <span>{device.region}</span>
          </div>
        )}
        {device.manufacturer && (
          <div className="text-xs">
            {device.manufacturer} {device.model && `• ${device.model}`}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between pt-3 border-t">
        <div className="text-xs text-gray-500">
          Last seen: {formatRelativeTime(device.last_seen)}
        </div>
        {device.active_alert_count > 0 && (
          <span className="px-2 py-1 text-xs font-medium bg-red-100 text-red-800 rounded">
            {device.active_alert_count} alert{device.active_alert_count > 1 ? 's' : ''}
          </span>
        )}
      </div>
    </Link>
  );
}

// Skeleton loader for device cards
function DeviceCardSkeleton() {
  return (
    <div className="bg-white rounded-lg shadow p-6 animate-pulse">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <div className="h-5 bg-gray-200 rounded w-3/4 mb-2"></div>
          <div className="h-4 bg-gray-200 rounded w-1/2"></div>
        </div>
        <div className="h-6 bg-gray-200 rounded w-16"></div>
      </div>
      <div className="space-y-2 mb-3">
        <div className="h-4 bg-gray-200 rounded w-1/3"></div>
        <div className="h-3 bg-gray-200 rounded w-1/2"></div>
      </div>
      <div className="h-4 bg-gray-200 rounded w-full"></div>
    </div>
  );
}

export default function Machines() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  // Debounce search input
  const handleSearchChange = (value: string) => {
    setSearch(value);
    // Debounce by 300ms
    const timer = setTimeout(() => {
      setDebouncedSearch(value);
      setPage(1); // Reset to first page on search
    }, 300);
    return () => clearTimeout(timer);
  };

  const { data, isLoading, isError, error } = useDevices({
    page,
    per_page: 20,
    search: debouncedSearch || undefined,
  });

  const devices = data?.data || [];
  const pagination = data?.pagination;

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Machines</h1>
            <p className="mt-2 text-gray-600">
              Manage and monitor all devices in your factory
            </p>
          </div>
          <Link
            to="/machines/new"
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700"
          >
            + Add Machine
          </Link>
        </div>

        {/* Search Bar */}
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <svg
              className="h-5 w-5 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>
          <input
            type="text"
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
            placeholder="Search by name, device key, or region..."
            className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
          />
        </div>
      </div>

      {/* Error State */}
      {isError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800 font-medium">Failed to load machines</p>
          <p className="text-red-600 text-sm mt-1">
            {error instanceof Error ? error.message : 'Unknown error'}
          </p>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {[...Array(8)].map((_, i) => (
            <DeviceCardSkeleton key={i} />
          ))}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !isError && devices.length === 0 && (
        <div className="bg-gray-50 border-2 border-dashed border-gray-300 rounded-lg p-12 text-center">
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
              d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"
            />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">No machines found</h3>
          <p className="mt-1 text-sm text-gray-500">
            {debouncedSearch
              ? 'Try adjusting your search terms.'
              : 'Get started by adding a new machine.'}
          </p>
          {!debouncedSearch && (
            <div className="mt-6">
              <Link
                to="/machines/new"
                className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
              >
                + Add Machine
              </Link>
            </div>
          )}
        </div>
      )}

      {/* Device Grid */}
      {!isLoading && !isError && devices.length > 0 && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mb-6">
            {devices.map((device) => (
              <DeviceCard key={device.id} device={device} />
            ))}
          </div>

          {/* Pagination */}
          {pagination && pagination.pages > 1 && (
            <div className="flex items-center justify-between border-t border-gray-200 bg-white px-4 py-3 sm:px-6 rounded-lg shadow">
              <div className="flex flex-1 justify-between sm:hidden">
                <button
                  onClick={() => setPage(page - 1)}
                  disabled={page === 1}
                  className="relative inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage(page + 1)}
                  disabled={page === pagination.pages}
                  className="relative ml-3 inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
              <div className="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm text-gray-700">
                    Showing page <span className="font-medium">{page}</span> of{' '}
                    <span className="font-medium">{pagination.pages}</span> (
                    <span className="font-medium">{pagination.total}</span> total)
                  </p>
                </div>
                <div>
                  <nav className="isolate inline-flex -space-x-px rounded-md shadow-sm" aria-label="Pagination">
                    <button
                      onClick={() => setPage(page - 1)}
                      disabled={page === 1}
                      className="relative inline-flex items-center rounded-l-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <span className="sr-only">Previous</span>
                      ←
                    </button>
                    {[...Array(pagination.pages)].map((_, i) => {
                      const pageNum = i + 1;
                      // Show first, last, current, and adjacent pages
                      if (
                        pageNum === 1 ||
                        pageNum === pagination.pages ||
                        (pageNum >= page - 1 && pageNum <= page + 1)
                      ) {
                        return (
                          <button
                            key={pageNum}
                            onClick={() => setPage(pageNum)}
                            className={`relative inline-flex items-center px-4 py-2 text-sm font-semibold ${
                              pageNum === page
                                ? 'z-10 bg-blue-600 text-white focus:z-20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600'
                                : 'text-gray-900 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0'
                            }`}
                          >
                            {pageNum}
                          </button>
                        );
                      } else if (pageNum === page - 2 || pageNum === page + 2) {
                        return (
                          <span
                            key={pageNum}
                            className="relative inline-flex items-center px-4 py-2 text-sm font-semibold text-gray-700 ring-1 ring-inset ring-gray-300"
                          >
                            ...
                          </span>
                        );
                      }
                      return null;
                    })}
                    <button
                      onClick={() => setPage(page + 1)}
                      disabled={page === pagination.pages}
                      className="relative inline-flex items-center rounded-r-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <span className="sr-only">Next</span>
                      →
                    </button>
                  </nav>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
