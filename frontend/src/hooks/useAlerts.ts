/**
 * React Query hooks for alerts.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { alerts } from '../api/endpoints';

export const useAlerts = (filters?: {
  device_id?: number;
  severity?: 'low' | 'medium' | 'high' | 'critical';
  resolved?: boolean;
  start?: string;
  end?: string;
  page?: number;
  per_page?: number;
}) => {
  return useQuery({
    queryKey: ['alerts', filters],
    queryFn: () => alerts.list(filters),
  });
};

export const useAlert = (alertId: number | undefined) => {
  return useQuery({
    queryKey: ['alerts', alertId],
    queryFn: () => alerts.get(alertId!),
    enabled: !!alertId,
  });
};

export const useResolveAlert = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (alertId: number) => alerts.resolve(alertId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
};
