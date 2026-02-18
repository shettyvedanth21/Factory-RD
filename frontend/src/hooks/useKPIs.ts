/**
 * React Query hooks for KPIs.
 */
import { useQuery } from '@tanstack/react-query';
import { kpis } from '../api/endpoints';

export const useKPIsLive = (deviceId: number | undefined) => {
  return useQuery({
    queryKey: ['kpis', 'live', deviceId],
    queryFn: () => kpis.live(deviceId!),
    enabled: !!deviceId,
    refetchInterval: 5000, // Refetch every 5 seconds
    staleTime: 3000, // Consider data stale after 3 seconds
  });
};

export const useKPIHistory = (
  deviceId: number | undefined,
  params: {
    parameter: string;
    start: string;
    end: string;
    interval?: string;
  } | undefined
) => {
  return useQuery({
    queryKey: ['kpis', 'history', deviceId, params],
    queryFn: () => kpis.history(deviceId!, params!),
    enabled: !!deviceId && !!params?.parameter,
  });
};
