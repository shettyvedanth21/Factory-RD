/**
 * Rule Builder Page
 * Creates or edits a rule with a 4-step form.
 */
import { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useRule, useCreateRule, useUpdateRule } from '../hooks/useRules';
import { useDevices } from '../hooks/useDevices';
import ConditionGroupEditor from '../components/rules/ConditionGroupEditor';
import type { ConditionTree, ConditionLeaf, DeviceParameter, RuleCreate } from '../types';

// Helper to check if condition is a leaf
function isConditionLeaf(condition: ConditionLeaf | ConditionTree): condition is ConditionLeaf {
  return 'parameter' in condition;
}

// Helper to generate plain English preview
function generateConditionPreview(condition: ConditionLeaf | ConditionTree, params: DeviceParameter[]): string {
  if (isConditionLeaf(condition)) {
    const param = params.find(p => p.parameter_key === condition.parameter);
    const paramName = param?.display_name || condition.parameter;
    const operators: Record<string, string> = {
      gt: '>',
      lt: '<',
      gte: '≥',
      lte: '≤',
      eq: '=',
      neq: '≠',
    };
    return `${paramName} ${operators[condition.operator]} ${condition.value}`;
  } else {
    const previews = condition.conditions.map(c => generateConditionPreview(c, params));
    return `(${previews.join(` ${condition.operator} `)})`;
  }
}

export default function RuleBuilder() {
  const { ruleId } = useParams<{ ruleId: string }>();
  const navigate = useNavigate();
  const isEditMode = !!ruleId && ruleId !== 'new';

  // Fetch existing rule if editing
  const { data: ruleData, isLoading: isLoadingRule } = useRule(
    isEditMode ? parseInt(ruleId!, 10) : undefined
  );

  // Fetch all devices for selection
  const { data: devicesData } = useDevices({ per_page: 100 });
  const devices = devicesData?.data || [];

  // Mutations
  const createRuleMutation = useCreateRule();
  const updateRuleMutation = useUpdateRule();

  // Form state
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    severity: 'medium' as 'low' | 'medium' | 'high' | 'critical',
    scope: 'device' as 'device' | 'global',
    device_ids: [] as number[],
    conditions: {
      operator: 'AND' as 'AND' | 'OR',
      conditions: [
        {
          parameter: '',
          operator: 'gt' as const,
          value: 0,
        },
      ],
    } as ConditionTree,
    schedule_type: 'always' as 'always' | 'time_window' | 'date_range',
    schedule_config: {} as any,
    cooldown_minutes: 30,
    notification_channels: {
      email: true,
      whatsapp: false,
    },
  });

  // Load existing rule data in edit mode
  useEffect(() => {
    if (isEditMode && ruleData?.data) {
      const rule = ruleData.data;
      setFormData({
        name: rule.name,
        description: rule.description || '',
        severity: rule.severity,
        scope: rule.scope,
        device_ids: rule.device_ids || [],
        conditions: rule.conditions,
        schedule_type: rule.schedule_type,
        schedule_config: rule.schedule_config || {},
        cooldown_minutes: rule.cooldown_minutes,
        notification_channels: rule.notification_channels,
      });
    }
  }, [isEditMode, ruleData]);

  // Get parameters from selected devices
  const availableParameters = useMemo(() => {
    if (formData.scope === 'global') {
      // For global rules, get all unique parameters across all devices
      const allParams = new Map<string, DeviceParameter>();
      devices.forEach(device => {
        device.parameters?.forEach(param => {
          if (!allParams.has(param.parameter_key)) {
            allParams.set(param.parameter_key, param);
          }
        });
      });
      return Array.from(allParams.values());
    } else {
      // For device-specific rules, get parameters from selected devices
      const selectedDevices = devices.filter(d => formData.device_ids.includes(d.id));
      const allParams = new Map<string, DeviceParameter>();
      selectedDevices.forEach(device => {
        device.parameters?.forEach(param => {
          if (!allParams.has(param.parameter_key)) {
            allParams.set(param.parameter_key, param);
          }
        });
      });
      return Array.from(allParams.values());
    }
  }, [formData.scope, formData.device_ids, devices]);

  // Validation
  const canProceed = (step: number): boolean => {
    switch (step) {
      case 1:
        return formData.name.trim() !== '';
      case 2:
        if (formData.scope === 'device') {
          return formData.device_ids.length > 0;
        }
        return true;
      case 3:
        return formData.conditions.conditions.length > 0;
      case 4:
        return true;
      default:
        return false;
    }
  };

  // Handle submit
  const handleSubmit = async () => {
    const payload: RuleCreate = {
      name: formData.name,
      description: formData.description || undefined,
      severity: formData.severity,
      scope: formData.scope,
      device_ids: formData.scope === 'device' ? formData.device_ids : undefined,
      conditions: formData.conditions,
      schedule_type: formData.schedule_type,
      schedule_config: formData.schedule_type !== 'always' ? formData.schedule_config : undefined,
      cooldown_minutes: formData.cooldown_minutes,
      notification_channels: formData.notification_channels,
    };

    try {
      if (isEditMode) {
        await updateRuleMutation.mutateAsync({
          ruleId: parseInt(ruleId!, 10),
          data: payload,
        });
      } else {
        await createRuleMutation.mutateAsync(payload);
      }
      navigate('/rules');
    } catch (error) {
      console.error('Failed to save rule:', error);
    }
  };

  if (isEditMode && isLoadingRule) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/3"></div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">
          {isEditMode ? 'Edit Rule' : 'Create New Rule'}
        </h1>
        <p className="mt-2 text-gray-600">
          Configure alert conditions and notification settings
        </p>
      </div>

      {/* Step Indicator */}
      <div className="mb-8">
        <div className="flex items-center justify-between max-w-3xl">
          {[1, 2, 3, 4].map((step) => (
            <div key={step} className="flex items-center flex-1">
              <div className="flex items-center">
                <div
                  className={`flex items-center justify-center w-10 h-10 rounded-full border-2 font-semibold ${
                    currentStep === step
                      ? 'border-blue-600 bg-blue-600 text-white'
                      : currentStep > step
                      ? 'border-green-600 bg-green-600 text-white'
                      : 'border-gray-300 bg-white text-gray-400'
                  }`}
                >
                  {currentStep > step ? '✓' : step}
                </div>
                <div className="ml-2 text-sm">
                  <div className={`font-medium ${currentStep >= step ? 'text-gray-900' : 'text-gray-400'}`}>
                    Step {step}
                  </div>
                  <div className="text-gray-500 text-xs">
                    {step === 1 && 'Basic Info'}
                    {step === 2 && 'Scope & Devices'}
                    {step === 3 && 'Conditions'}
                    {step === 4 && 'Schedule & Notify'}
                  </div>
                </div>
              </div>
              {step < 4 && (
                <div className={`flex-1 h-0.5 mx-4 ${currentStep > step ? 'bg-green-600' : 'bg-gray-300'}`} />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Form Content */}
      <div className="bg-white rounded-lg shadow p-6 max-w-4xl">
        {/* Step 1: Basic Info */}
        {currentStep === 1 && (
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Rule Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g., High Voltage Alert"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Optional description of what this rule monitors"
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Severity
              </label>
              <div className="grid grid-cols-4 gap-2">
                {(['low', 'medium', 'high', 'critical'] as const).map((severity) => (
                  <button
                    key={severity}
                    onClick={() => setFormData({ ...formData, severity })}
                    className={`px-4 py-2 rounded-md font-medium transition-colors ${
                      formData.severity === severity
                        ? severity === 'critical'
                          ? 'bg-red-600 text-white'
                          : severity === 'high'
                          ? 'bg-orange-600 text-white'
                          : severity === 'medium'
                          ? 'bg-yellow-600 text-white'
                          : 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {severity.charAt(0).toUpperCase() + severity.slice(1)}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Scope & Devices */}
        {currentStep === 2 && (
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Rule Scope
              </label>
              <div className="grid grid-cols-2 gap-4">
                <button
                  onClick={() => setFormData({ ...formData, scope: 'device', device_ids: [] })}
                  className={`p-4 rounded-lg border-2 text-left transition-colors ${
                    formData.scope === 'device'
                      ? 'border-blue-600 bg-blue-50'
                      : 'border-gray-300 hover:border-gray-400'
                  }`}
                >
                  <div className="font-medium text-gray-900">Device-specific</div>
                  <div className="text-sm text-gray-600 mt-1">
                    Apply to selected devices only
                  </div>
                </button>
                <button
                  onClick={() => setFormData({ ...formData, scope: 'global', device_ids: [] })}
                  className={`p-4 rounded-lg border-2 text-left transition-colors ${
                    formData.scope === 'global'
                      ? 'border-purple-600 bg-purple-50'
                      : 'border-gray-300 hover:border-gray-400'
                  }`}
                >
                  <div className="font-medium text-gray-900">Global</div>
                  <div className="text-sm text-gray-600 mt-1">
                    Apply to all factory devices
                  </div>
                </button>
              </div>
            </div>

            {formData.scope === 'device' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Select Devices <span className="text-red-500">*</span>
                </label>
                <div className="border border-gray-300 rounded-md max-h-64 overflow-y-auto">
                  {devices.map((device) => (
                    <label
                      key={device.id}
                      className="flex items-center p-3 hover:bg-gray-50 cursor-pointer border-b last:border-b-0"
                    >
                      <input
                        type="checkbox"
                        checked={formData.device_ids.includes(device.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setFormData({
                              ...formData,
                              device_ids: [...formData.device_ids, device.id],
                            });
                          } else {
                            setFormData({
                              ...formData,
                              device_ids: formData.device_ids.filter((id) => id !== device.id),
                            });
                          }
                        }}
                        className="mr-3 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <div className="flex-1">
                        <div className="font-medium text-gray-900">
                          {device.name || device.device_key}
                        </div>
                        <div className="text-sm text-gray-500">
                          {device.device_key} {device.region && `• ${device.region}`}
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
                <div className="mt-2 text-sm text-gray-600">
                  {formData.device_ids.length} device{formData.device_ids.length !== 1 ? 's' : ''} selected
                </div>
              </div>
            )}

            {formData.scope === 'global' && (
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                <div className="flex items-start">
                  <svg className="w-5 h-5 text-purple-600 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-purple-800">Global Rule</h3>
                    <p className="mt-1 text-sm text-purple-700">
                      This rule will apply to all devices in your factory, including future devices.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Step 3: Conditions */}
        {currentStep === 3 && (
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">
                Alert Conditions <span className="text-red-500">*</span>
              </label>
              <ConditionGroupEditor
                group={formData.conditions}
                parameters={availableParameters}
                onChange={(updated) => setFormData({ ...formData, conditions: updated })}
              />
            </div>

            {/* Plain English Preview */}
            {formData.conditions.conditions.length > 0 && availableParameters.length > 0 && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="text-sm font-medium text-blue-900 mb-1">Plain English:</div>
                <div className="text-sm text-blue-800">
                  Alert when <strong>{generateConditionPreview(formData.conditions, availableParameters)}</strong>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Step 4: Schedule & Notifications */}
        {currentStep === 4 && (
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Schedule Type
              </label>
              <div className="space-y-2">
                <label className="flex items-center p-3 border rounded-md cursor-pointer hover:bg-gray-50">
                  <input
                    type="radio"
                    checked={formData.schedule_type === 'always'}
                    onChange={() => setFormData({ ...formData, schedule_type: 'always' })}
                    className="mr-3 h-4 w-4 text-blue-600 focus:ring-blue-500"
                  />
                  <div>
                    <div className="font-medium text-gray-900">Always</div>
                    <div className="text-sm text-gray-500">Monitor 24/7</div>
                  </div>
                </label>
                <label className="flex items-center p-3 border rounded-md cursor-pointer hover:bg-gray-50">
                  <input
                    type="radio"
                    checked={formData.schedule_type === 'time_window'}
                    onChange={() => setFormData({ ...formData, schedule_type: 'time_window' })}
                    className="mr-3 h-4 w-4 text-blue-600 focus:ring-blue-500"
                  />
                  <div>
                    <div className="font-medium text-gray-900">Time Window</div>
                    <div className="text-sm text-gray-500">Specific days and hours</div>
                  </div>
                </label>
                <label className="flex items-center p-3 border rounded-md cursor-pointer hover:bg-gray-50">
                  <input
                    type="radio"
                    checked={formData.schedule_type === 'date_range'}
                    onChange={() => setFormData({ ...formData, schedule_type: 'date_range' })}
                    className="mr-3 h-4 w-4 text-blue-600 focus:ring-blue-500"
                  />
                  <div>
                    <div className="font-medium text-gray-900">Date Range</div>
                    <div className="text-sm text-gray-500">Between specific dates</div>
                  </div>
                </label>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Cooldown Period (minutes)
              </label>
              <input
                type="number"
                value={formData.cooldown_minutes}
                onChange={(e) => setFormData({ ...formData, cooldown_minutes: parseInt(e.target.value) || 0 })}
                min={0}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
              <p className="mt-1 text-sm text-gray-500">
                Minimum time between alerts for the same device
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Notification Channels
              </label>
              <div className="space-y-2">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.notification_channels.email}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        notification_channels: {
                          ...formData.notification_channels,
                          email: e.target.checked,
                        },
                      })
                    }
                    className="mr-3 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <span className="text-gray-900">Email notifications</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.notification_channels.whatsapp}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        notification_channels: {
                          ...formData.notification_channels,
                          whatsapp: e.target.checked,
                        },
                      })
                    }
                    className="mr-3 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <span className="text-gray-900">WhatsApp notifications</span>
                </label>
              </div>
            </div>
          </div>
        )}

        {/* Navigation Buttons */}
        <div className="mt-8 flex items-center justify-between pt-6 border-t">
          <button
            onClick={() => setCurrentStep(Math.max(1, currentStep - 1))}
            disabled={currentStep === 1}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            ← Previous
          </button>

          <div className="flex gap-2">
            <button
              onClick={() => navigate('/rules')}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Cancel
            </button>

            {currentStep < 4 ? (
              <button
                onClick={() => setCurrentStep(currentStep + 1)}
                disabled={!canProceed(currentStep)}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next →
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={!canProceed(currentStep) || createRuleMutation.isPending || updateRuleMutation.isPending}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {createRuleMutation.isPending || updateRuleMutation.isPending
                  ? 'Saving...'
                  : isEditMode
                  ? 'Update Rule'
                  : 'Create Rule'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
