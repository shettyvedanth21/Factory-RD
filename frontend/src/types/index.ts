/**
 * TypeScript type definitions for FactoryOps frontend.
 * These types match the API schemas from api-spec.md.
 */

// ===== Common Types =====

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    pages: number;
  };
}

export interface ApiResponse<T> {
  data: T;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: any;
  };
}

// ===== Factory & Auth =====

export interface Factory {
  id: number;
  name: string;
  slug: string;
}

export interface User {
  id: number;
  email: string;
  role: 'super_admin' | 'admin';
  permissions: Record<string, boolean>;
}

export interface AuthState {
  user: User | null;
  factory: Factory | null;
  token: string | null;
  isAuthenticated: boolean;
}

export interface LoginRequest {
  factory_id: number;
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

// ===== Devices =====

export interface Device {
  id: number;
  device_key: string;
  name: string | null;
  manufacturer: string | null;
  model: string | null;
  region: string | null;
  api_key: string | null;
  is_active: boolean;
  last_seen: string | null;
  created_at: string;
  updated_at: string;
  parameters?: DeviceParameter[];
}

export interface DeviceListItem {
  id: number;
  device_key: string;
  name: string | null;
  manufacturer: string | null;
  region: string | null;
  is_active: boolean;
  last_seen: string | null;
  health_score: number;
  active_alert_count: number;
  current_energy_kw: number;
}

export interface DeviceCreate {
  device_key: string;
  name?: string;
  manufacturer?: string;
  model?: string;
  region?: string;
}

export interface DeviceUpdate {
  name?: string;
  manufacturer?: string;
  model?: string;
  region?: string;
  is_active?: boolean;
}

// ===== Device Parameters =====

export interface DeviceParameter {
  id: number;
  parameter_key: string;
  display_name: string | null;
  unit: string | null;
  data_type: 'float' | 'int' | 'string';
  is_kpi_selected: boolean;
  discovered_at: string;
  updated_at: string;
}

export interface ParameterUpdate {
  display_name?: string;
  unit?: string;
  is_kpi_selected?: boolean;
}

// ===== KPIs =====

export interface KPIValue {
  parameter_key: string;
  display_name: string | null;
  unit: string | null;
  value: number;
  is_stale: boolean;
}

export interface KPILiveResponse {
  device_id: number;
  timestamp: string;
  kpis: KPIValue[];
}

export interface DataPoint {
  timestamp: string;
  value: number;
}

export interface KPIHistoryResponse {
  parameter_key: string;
  display_name: string | null;
  unit: string | null;
  interval: string;
  points: DataPoint[];
}

// ===== Rules =====

export interface ConditionLeaf {
  parameter: string;
  operator: 'gt' | 'lt' | 'gte' | 'lte' | 'eq' | 'neq';
  value: number;
}

export interface ConditionTree {
  operator: 'AND' | 'OR';
  conditions: (ConditionLeaf | ConditionTree)[];
}

export interface Rule {
  id: number;
  name: string;
  description: string | null;
  scope: 'device' | 'global';
  device_ids: number[];
  conditions: ConditionTree;
  cooldown_minutes: number;
  is_active: boolean;
  schedule_type: 'always' | 'time_window' | 'date_range';
  schedule_config: any;
  severity: 'low' | 'medium' | 'high' | 'critical';
  notification_channels: {
    email: boolean;
    whatsapp: boolean;
  };
  created_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface RuleCreate {
  name: string;
  description?: string;
  scope: 'device' | 'global';
  device_ids?: number[];
  conditions: ConditionTree;
  cooldown_minutes?: number;
  severity?: 'low' | 'medium' | 'high' | 'critical';
  schedule_type?: 'always' | 'time_window' | 'date_range';
  schedule_config?: any;
  notification_channels?: {
    email: boolean;
    whatsapp: boolean;
  };
}

export interface RuleUpdate {
  name?: string;
  description?: string;
  scope?: 'device' | 'global';
  device_ids?: number[];
  conditions?: ConditionTree;
  cooldown_minutes?: number;
  severity?: 'low' | 'medium' | 'high' | 'critical';
  schedule_type?: 'always' | 'time_window' | 'date_range';
  schedule_config?: any;
  notification_channels?: {
    email: boolean;
    whatsapp: boolean;
  };
  is_active?: boolean;
}

// ===== Alerts =====

export interface Alert {
  id: number;
  rule_id: number;
  rule_name: string;
  device_id: number;
  device_name: string | null;
  triggered_at: string;
  resolved_at: string | null;
  severity: 'low' | 'medium' | 'high' | 'critical';
  message: string | null;
  telemetry_snapshot: Record<string, any> | null;
  notification_sent: boolean;
  created_at: string;
}

// ===== Analytics =====

export interface AnalyticsJob {
  id: string;
  factory_id: number;
  created_by: number;
  job_type: 'anomaly' | 'failure_prediction' | 'energy_forecast' | 'ai_copilot';
  mode: 'standard' | 'ai_copilot';
  device_ids: number[];
  date_range_start: string;
  date_range_end: string;
  status: 'pending' | 'running' | 'complete' | 'failed';
  result_url: string | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface AnalyticsJobCreate {
  job_type: 'anomaly' | 'failure_prediction' | 'energy_forecast' | 'ai_copilot';
  mode?: 'standard' | 'ai_copilot';
  device_ids: number[];
  date_range_start: string;
  date_range_end: string;
}

// ===== Reports =====

export interface Report {
  id: string;
  factory_id: number;
  created_by: number;
  title: string | null;
  device_ids: number[];
  date_range_start: string;
  date_range_end: string;
  format: 'pdf' | 'excel' | 'json';
  include_analytics: boolean;
  analytics_job_id: string | null;
  status: 'pending' | 'running' | 'complete' | 'failed';
  file_url: string | null;
  file_size_bytes: number | null;
  error_message: string | null;
  expires_at: string | null;
  created_at: string;
}

export interface ReportCreate {
  title?: string;
  device_ids: number[];
  date_range_start: string;
  date_range_end: string;
  format: 'pdf' | 'excel' | 'json';
  include_analytics?: boolean;
  analytics_job_id?: string;
}

// ===== Dashboard =====

export interface DashboardSummary {
  total_devices: number;
  active_devices: number;
  offline_devices: number;
  active_alerts: number;
  critical_alerts: number;
  current_energy_kw: number;
  health_score: number;
  energy_today_kwh: number;
  energy_this_month_kwh: number;
}

// ===== UI State =====

export interface AppNotification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  duration?: number;
}
