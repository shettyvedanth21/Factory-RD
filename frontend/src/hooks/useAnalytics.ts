/**
 * React Query hooks for analytics operations.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';

interface AnalyticsJob {
  id: string;
  factory_id: number;
  job_type: string;
  mode: string;
  device_ids: number[];
  date_range_start: string;
  date_range_end: string;
  status: string;
  result_url?: string;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

interface CreateAnalyticsJobParams {
  job_type: string;
  device_ids: number[];
  date_range_start: string;
  date_range_end: string;
  mode?: string;
}

interface AnalyticsJobsParams {
  job_type?: string;
  status?: string;
  page?: number;
  per_page?: number;
}

export function useAnalyticsJobs(params?: AnalyticsJobsParams) {
  return useQuery({
    queryKey: ['analytics-jobs', params],
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      if (params?.job_type) searchParams.append('job_type', params.job_type);
      if (params?.status) searchParams.append('status', params.status);
      if (params?.page) searchParams.append('page', params.page.toString());
      if (params?.per_page) searchParams.append('per_page', params.per_page.toString());
      
      const response = await apiClient.get(`/analytics/jobs?${searchParams.toString()}`);
      return response.data;
    },
    refetchInterval: (data) => {
      // Auto-refresh every 3 seconds if there are running/pending jobs
      const hasActiveJobs = data?.data?.some((job: AnalyticsJob) => 
        job.status === 'running' || job.status === 'pending'
      );
      return hasActiveJobs ? 3000 : false;
    },
  });
}

export function useAnalyticsJob(jobId?: string) {
  return useQuery({
    queryKey: ['analytics-job', jobId],
    queryFn: async () => {
      const response = await apiClient.get(`/analytics/jobs/${jobId}`);
      return response.data;
    },
    enabled: !!jobId,
    refetchInterval: (data) => {
      // Poll every 3 seconds if job is running or pending
      const status = data?.data?.status;
      return status === 'running' || status === 'pending' ? 3000 : false;
    },
  });
}

export function useCreateAnalyticsJob() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (params: CreateAnalyticsJobParams) => {
      const response = await apiClient.post('/analytics/jobs', params);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['analytics-jobs'] });
    },
  });
}

export function useDeleteAnalyticsJob() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (jobId: string) => {
      await apiClient.delete(`/analytics/jobs/${jobId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['analytics-jobs'] });
    },
  });
}
