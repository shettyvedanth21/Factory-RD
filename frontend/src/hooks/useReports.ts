/**
 * React Query hooks for reports operations.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';

interface Report {
  id: string;
  factory_id: number;
  title?: string;
  device_ids: number[];
  date_range_start: string;
  date_range_end: string;
  format: string;
  include_analytics: boolean;
  analytics_job_id?: string;
  status: string;
  file_url?: string;
  file_size_bytes?: number;
  error_message?: string;
  expires_at?: string;
  created_at: string;
}

interface CreateReportParams {
  title?: string;
  device_ids: number[];
  date_range_start: string;
  date_range_end: string;
  format: string;
  include_analytics?: boolean;
  analytics_job_id?: string;
}

interface ReportsParams {
  format?: string;
  status?: string;
  page?: number;
  per_page?: number;
}

export function useReports(params?: ReportsParams) {
  return useQuery({
    queryKey: ['reports', params],
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      if (params?.format) searchParams.append('format', params.format);
      if (params?.status) searchParams.append('status', params.status);
      if (params?.page) searchParams.append('page', params.page.toString());
      if (params?.per_page) searchParams.append('per_page', params.per_page.toString());
      
      const response = await apiClient.get(`/reports?${searchParams.toString()}`);
      return response.data;
    },
    refetchInterval: (data) => {
      // Auto-refresh every 5 seconds if there are running/pending reports
      const hasActiveReports = data?.data?.some((report: Report) => 
        report.status === 'running' || report.status === 'pending'
      );
      return hasActiveReports ? 5000 : false;
    },
  });
}

export function useReport(reportId?: string) {
  return useQuery({
    queryKey: ['report', reportId],
    queryFn: async () => {
      const response = await apiClient.get(`/reports/${reportId}`);
      return response.data;
    },
    enabled: !!reportId,
    refetchInterval: (data) => {
      // Poll every 5 seconds if report is running or pending
      const status = data?.data?.status;
      return status === 'running' || status === 'pending' ? 5000 : false;
    },
  });
}

export function useCreateReport() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (params: CreateReportParams) => {
      const response = await apiClient.post('/reports', params);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] });
    },
  });
}
