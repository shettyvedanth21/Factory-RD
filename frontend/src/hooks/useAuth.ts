/**
 * React Query hooks for authentication.
 */
import { useMutation } from '@tanstack/react-query';
import { auth } from '../api/endpoints';
import { useAuthStore } from '../stores/authStore';
import type { LoginRequest } from '../types';

export const useLogin = () => {
  const setAuth = useAuthStore((state) => state.setAuth);

  return useMutation({
    mutationFn: auth.login,
    onSuccess: (data) => {
      // Extract factory from selectedFactory in sessionStorage
      const factoryData = sessionStorage.getItem('selectedFactory');
      if (factoryData) {
        const factory = JSON.parse(factoryData);
        setAuth(data.access_token, data.user, factory);
      }
    },
  });
};

export const useLogout = () => {
  const logout = useAuthStore((state) => state.logout);

  return () => {
    logout();
    window.location.href = '/factory-select';
  };
};
