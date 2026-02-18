/**
 * Hook for user management operations.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';

interface User {
  id: number;
  email: string;
  whatsapp_number?: string;
  role: string;
  permissions: Record<string, boolean>;
  is_active: boolean;
  last_login?: string;
  created_at: string;
}

interface InviteUserRequest {
  email: string;
  whatsapp_number?: string;
  permissions: {
    can_create_rules: boolean;
    can_run_analytics: boolean;
    can_generate_reports: boolean;
  };
}

interface UpdatePermissionsRequest {
  permissions: Record<string, boolean>;
}

export function useUsers() {
  return useQuery({
    queryKey: ['users'],
    queryFn: async () => {
      const response = await apiClient.get('/users');
      return response.data;
    },
  });
}

export function useInviteUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: InviteUserRequest) => {
      const response = await apiClient.post('/users/invite', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
}

export function useUpdateUserPermissions() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ userId, permissions }: { userId: number; permissions: Record<string, boolean> }) => {
      const response = await apiClient.patch(`/users/${userId}/permissions`, { permissions });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
}

export function useDeactivateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (userId: number) => {
      await apiClient.delete(`/users/${userId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
}
