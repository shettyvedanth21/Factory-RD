/**
 * React Query hooks for devices.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { devices } from '../api/endpoints';
import type { DeviceCreate, DeviceUpdate } from '../types';

export const useDevices = (filters?: {
  page?: number;
  per_page?: number;
  search?: string;
  is_active?: boolean;
}) => {
  return useQuery({
    queryKey: ['devices', filters],
    queryFn: () => devices.list(filters),
  });
};

export const useDevice = (deviceId: number | undefined) => {
  return useQuery({
    queryKey: ['devices', deviceId],
    queryFn: () => devices.get(deviceId!),
    enabled: !!deviceId,
  });
};

export const useCreateDevice = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: DeviceCreate) => devices.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['devices'] });
    },
  });
};

export const useUpdateDevice = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ deviceId, data }: { deviceId: number; data: DeviceUpdate }) =>
      devices.update(deviceId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['devices'] });
      queryClient.invalidateQueries({ queryKey: ['devices', variables.deviceId] });
    },
  });
};

export const useDeleteDevice = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (deviceId: number) => devices.delete(deviceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['devices'] });
    },
  });
};
