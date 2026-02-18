/**
 * Typed API endpoint functions matching api-spec.md.
 * All functions are grouped by domain and return promises.
 */
import api from './client';
import type {
  Factory,
  LoginRequest,
  LoginResponse,
  Device,
  DeviceListItem,
  DeviceCreate,
  DeviceUpdate,
  DeviceParameter,
  ParameterUpdate,
  KPILiveResponse,
  KPIHistoryResponse,
  Rule,
  RuleCreate,
  RuleUpdate,
  Alert,
  AnalyticsJob,
  AnalyticsJobCreate,
  Report,
  ReportCreate,
  DashboardSummary,
  PaginatedResponse,
  ApiResponse,
} from '../types';

// ===== Auth =====

export const auth = {
  getFactories: async (): Promise<Factory[]> => {
    const response = await api.get<ApiResponse<Factory[]>>('/factories');
    return response.data.data;
  },

  login: async (data: LoginRequest): Promise<LoginResponse> => {
    const response = await api.post<ApiResponse<LoginResponse>>('/auth/login', data);
    return response.data.data;
  },

  refresh: async (): Promise<LoginResponse> => {
    const response = await api.post<ApiResponse<LoginResponse>>('/auth/refresh');
    return response.data.data;
  },
};

// ===== Devices =====

export const devices = {
  list: async (params?: {
    page?: number;
    per_page?: number;
    search?: string;
    is_active?: boolean;
  }): Promise<PaginatedResponse<DeviceListItem>> => {
    const response = await api.get<PaginatedResponse<DeviceListItem>>('/devices', { params });
    return response.data;
  },

  get: async (deviceId: number): Promise<Device> => {
    const response = await api.get<ApiResponse<Device>>(`/devices/${deviceId}`);
    return response.data.data;
  },

  create: async (data: DeviceCreate): Promise<Device> => {
    const response = await api.post<ApiResponse<Device>>('/devices', data);
    return response.data.data;
  },

  update: async (deviceId: number, data: DeviceUpdate): Promise<Device> => {
    const response = await api.patch<ApiResponse<Device>>(`/devices/${deviceId}`, data);
    return response.data.data;
  },

  delete: async (deviceId: number): Promise<void> => {
    await api.delete(`/devices/${deviceId}`);
  },
};

// ===== Parameters =====

export const parameters = {
  list: async (deviceId: number): Promise<DeviceParameter[]> => {
    const response = await api.get<ApiResponse<DeviceParameter[]>>(`/devices/${deviceId}/parameters`);
    return response.data.data;
  },

  update: async (deviceId: number, paramId: number, data: ParameterUpdate): Promise<DeviceParameter> => {
    const response = await api.patch<ApiResponse<DeviceParameter>>(
      `/devices/${deviceId}/parameters/${paramId}`,
      data
    );
    return response.data.data;
  },
};

// ===== KPIs =====

export const kpis = {
  live: async (deviceId: number): Promise<KPILiveResponse> => {
    const response = await api.get<ApiResponse<KPILiveResponse>>(`/devices/${deviceId}/kpis/live`);
    return response.data.data;
  },

  history: async (
    deviceId: number,
    params: {
      parameter: string;
      start: string;
      end: string;
      interval?: string;
    }
  ): Promise<KPIHistoryResponse> => {
    const response = await api.get<ApiResponse<KPIHistoryResponse>>(`/devices/${deviceId}/kpis/history`, {
      params,
    });
    return response.data.data;
  },
};

// ===== Rules =====

export const rules = {
  list: async (params?: {
    device_id?: number;
    is_active?: boolean;
    scope?: 'device' | 'global';
    page?: number;
    per_page?: number;
  }): Promise<PaginatedResponse<Rule>> => {
    const response = await api.get<PaginatedResponse<Rule>>('/rules', { params });
    return response.data;
  },

  get: async (ruleId: number): Promise<Rule> => {
    const response = await api.get<ApiResponse<Rule>>(`/rules/${ruleId}`);
    return response.data.data;
  },

  create: async (data: RuleCreate): Promise<Rule> => {
    const response = await api.post<ApiResponse<Rule>>('/rules', data);
    return response.data.data;
  },

  update: async (ruleId: number, data: RuleUpdate): Promise<Rule> => {
    const response = await api.patch<ApiResponse<Rule>>(`/rules/${ruleId}`, data);
    return response.data.data;
  },

  delete: async (ruleId: number): Promise<void> => {
    await api.delete(`/rules/${ruleId}`);
  },

  toggle: async (ruleId: number): Promise<Rule> => {
    const response = await api.patch<ApiResponse<Rule>>(`/rules/${ruleId}/toggle`);
    return response.data.data;
  },
};

// ===== Alerts =====

export const alerts = {
  list: async (params?: {
    device_id?: number;
    severity?: 'low' | 'medium' | 'high' | 'critical';
    resolved?: boolean;
    start?: string;
    end?: string;
    page?: number;
    per_page?: number;
  }): Promise<PaginatedResponse<Alert>> => {
    const response = await api.get<PaginatedResponse<Alert>>('/alerts', { params });
    return response.data;
  },

  get: async (alertId: number): Promise<Alert> => {
    const response = await api.get<ApiResponse<Alert>>(`/alerts/${alertId}`);
    return response.data.data;
  },

  resolve: async (alertId: number): Promise<Alert> => {
    const response = await api.patch<ApiResponse<Alert>>(`/alerts/${alertId}/resolve`);
    return response.data.data;
  },
};

// ===== Analytics =====

export const analytics = {
  createJob: async (data: AnalyticsJobCreate): Promise<AnalyticsJob> => {
    const response = await api.post<ApiResponse<AnalyticsJob>>('/analytics/jobs', data);
    return response.data.data;
  },

  getJob: async (jobId: string): Promise<AnalyticsJob> => {
    const response = await api.get<ApiResponse<AnalyticsJob>>(`/analytics/jobs/${jobId}`);
    return response.data.data;
  },

  listJobs: async (params?: {
    job_type?: string;
    status?: string;
    page?: number;
    per_page?: number;
  }): Promise<PaginatedResponse<AnalyticsJob>> => {
    const response = await api.get<PaginatedResponse<AnalyticsJob>>('/analytics/jobs', { params });
    return response.data;
  },
};

// ===== Reports =====

export const reports = {
  create: async (data: ReportCreate): Promise<Report> => {
    const response = await api.post<ApiResponse<Report>>('/reports', data);
    return response.data.data;
  },

  get: async (reportId: string): Promise<Report> => {
    const response = await api.get<ApiResponse<Report>>(`/reports/${reportId}`);
    return response.data.data;
  },

  list: async (params?: {
    status?: string;
    page?: number;
    per_page?: number;
  }): Promise<PaginatedResponse<Report>> => {
    const response = await api.get<PaginatedResponse<Report>>('/reports', { params });
    return response.data;
  },

  download: async (reportId: string): Promise<Blob> => {
    const response = await api.get(`/reports/${reportId}/download`, {
      responseType: 'blob',
    });
    return response.data;
  },
};

// ===== Dashboard =====

export const dashboard = {
  getSummary: async (): Promise<DashboardSummary> => {
    const response = await api.get<ApiResponse<DashboardSummary>>('/dashboard/summary');
    return response.data.data;
  },
};
