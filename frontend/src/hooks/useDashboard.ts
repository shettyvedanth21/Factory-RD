/**
 * React Query hooks for dashboard.
 */
import { useQuery } from '@tanstack/react-query';
import { dashboard } from '../api/endpoints';

export const useDashboardSummary = () => {
  return useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: () => dashboard.getSummary(),
    refetchInterval: 30000, // Refetch every 30 seconds
    staleTime: 20000, // Consider data stale after 20 seconds
  });
};
