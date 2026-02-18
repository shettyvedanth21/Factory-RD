/**
 * React Query hooks for rules.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { rules } from '../api/endpoints';
import type { RuleCreate, RuleUpdate } from '../types';

export const useRules = (filters?: {
  device_id?: number;
  is_active?: boolean;
  scope?: 'device' | 'global';
  page?: number;
  per_page?: number;
}) => {
  return useQuery({
    queryKey: ['rules', filters],
    queryFn: () => rules.list(filters),
  });
};

export const useRule = (ruleId: number | undefined) => {
  return useQuery({
    queryKey: ['rules', ruleId],
    queryFn: () => rules.get(ruleId!),
    enabled: !!ruleId,
  });
};

export const useCreateRule = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: RuleCreate) => rules.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] });
    },
  });
};

export const useUpdateRule = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ ruleId, data }: { ruleId: number; data: RuleUpdate }) =>
      rules.update(ruleId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['rules'] });
      queryClient.invalidateQueries({ queryKey: ['rules', variables.ruleId] });
    },
  });
};

export const useToggleRule = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (ruleId: number) => rules.toggle(ruleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] });
    },
  });
};

export const useDeleteRule = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (ruleId: number) => rules.delete(ruleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] });
    },
  });
};
