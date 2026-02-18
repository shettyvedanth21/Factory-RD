/**
 * Users management page - super admin only.
 */
import { useState } from 'react';
import { useUsers, useInviteUser, useUpdateUserPermissions, useDeactivateUser } from '../hooks/useUsers';

// Permission toggle component
function PermissionToggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-2 cursor-pointer">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
      />
      <span className="text-sm text-gray-700">{label}</span>
    </label>
  );
}

// Invite User Modal
function InviteUserModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const [email, setEmail] = useState('');
  const [whatsappNumber, setWhatsappNumber] = useState('');
  const [permissions, setPermissions] = useState({
    can_create_rules: true,
    can_run_analytics: true,
    can_generate_reports: true,
  });

  const inviteMutation = useInviteUser();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      await inviteMutation.mutateAsync({
        email,
        whatsapp_number: whatsappNumber || undefined,
        permissions,
      });

      // Success toast
      alert('Invitation sent successfully!');

      // Reset form
      setEmail('');
      setWhatsappNumber('');
      setPermissions({
        can_create_rules: true,
        can_run_analytics: true,
        can_generate_reports: true,
      });
      onClose();
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to send invitation');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Invite Admin User</h2>

        <form onSubmit={handleSubmit}>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email <span className="text-red-500">*</span>
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="user@example.com"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">WhatsApp Number</label>
              <input
                type="tel"
                value={whatsappNumber}
                onChange={(e) => setWhatsappNumber(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="+919876543210"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Permissions</label>
              <div className="space-y-2">
                <PermissionToggle
                  label="Create Rules"
                  checked={permissions.can_create_rules}
                  onChange={(checked) =>
                    setPermissions((prev) => ({ ...prev, can_create_rules: checked }))
                  }
                />
                <PermissionToggle
                  label="Run Analytics"
                  checked={permissions.can_run_analytics}
                  onChange={(checked) =>
                    setPermissions((prev) => ({ ...prev, can_run_analytics: checked }))
                  }
                />
                <PermissionToggle
                  label="Generate Reports"
                  checked={permissions.can_generate_reports}
                  onChange={(checked) =>
                    setPermissions((prev) => ({ ...prev, can_generate_reports: checked }))
                  }
                />
              </div>
            </div>
          </div>

          <div className="flex gap-3 mt-6">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={inviteMutation.isPending}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {inviteMutation.isPending ? 'Sending...' : 'Send Invite'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Edit Permissions Drawer
function EditPermissionsDrawer({
  user,
  isOpen,
  onClose,
}: {
  user: any;
  isOpen: boolean;
  onClose: () => void;
}) {
  const [permissions, setPermissions] = useState(user?.permissions || {});
  const updateMutation = useUpdateUserPermissions();

  const handleSave = async () => {
    try {
      await updateMutation.mutateAsync({
        userId: user.id,
        permissions,
      });
      alert('Permissions updated successfully!');
      onClose();
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to update permissions');
    }
  };

  if (!isOpen || !user) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-end justify-end z-50">
      <div className="bg-white w-96 h-full shadow-xl p-6 overflow-y-auto">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Edit Permissions</h2>
        <p className="text-sm text-gray-600 mb-6">{user.email}</p>

        <div className="space-y-3 mb-6">
          <PermissionToggle
            label="Create Rules"
            checked={permissions.can_create_rules || false}
            onChange={(checked) =>
              setPermissions((prev: any) => ({ ...prev, can_create_rules: checked }))
            }
          />
          <PermissionToggle
            label="Run Analytics"
            checked={permissions.can_run_analytics || false}
            onChange={(checked) =>
              setPermissions((prev: any) => ({ ...prev, can_run_analytics: checked }))
            }
          />
          <PermissionToggle
            label="Generate Reports"
            checked={permissions.can_generate_reports || false}
            onChange={(checked) =>
              setPermissions((prev: any) => ({ ...prev, can_generate_reports: checked }))
            }
          />
        </div>

        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={updateMutation.isPending}
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {updateMutation.isPending ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function UsersPage() {
  const { data, isLoading, isError, error } = useUsers();
  const deactivateMutation = useDeactivateUser();

  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<any>(null);

  const users = data?.data || [];

  const handleDeactivate = async (userId: number, userEmail: string) => {
    if (!confirm(`Are you sure you want to deactivate ${userEmail}?`)) {
      return;
    }

    try {
      await deactivateMutation.mutateAsync(userId);
      alert('User deactivated successfully!');
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to deactivate user');
    }
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Users</h1>
          <p className="mt-2 text-gray-600">Manage admin users and permissions</p>
        </div>
        <button
          onClick={() => setIsInviteModalOpen(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
        >
          + Invite Admin
        </button>
      </div>

      {/* Error State */}
      {isError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800 font-medium">Failed to load users</p>
          <p className="text-red-600 text-sm mt-1">
            {error instanceof Error ? error.message : 'Unknown error'}
          </p>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading users...</p>
        </div>
      )}

      {/* Users Table */}
      {!isLoading && !isError && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  User
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Role
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Permissions
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Last Login
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {users.map((user: any) => (
                <tr key={user.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">{user.email}</div>
                    {user.whatsapp_number && (
                      <div className="text-sm text-gray-500">{user.whatsapp_number}</div>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`px-2 py-1 text-xs font-medium rounded ${
                        user.role === 'super_admin'
                          ? 'bg-purple-100 text-purple-800'
                          : 'bg-blue-100 text-blue-800'
                      }`}
                    >
                      {user.role === 'super_admin' ? 'Super Admin' : 'Admin'}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex flex-wrap gap-1">
                      {user.permissions?.can_create_rules && (
                        <span className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded">
                          Rules
                        </span>
                      )}
                      {user.permissions?.can_run_analytics && (
                        <span className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded">
                          Analytics
                        </span>
                      )}
                      {user.permissions?.can_generate_reports && (
                        <span className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded">
                          Reports
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`px-2 py-1 text-xs font-medium rounded ${
                        user.is_active
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {user.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {user.last_login
                      ? new Date(user.last_login).toLocaleDateString()
                      : 'Never'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div className="flex justify-end gap-2">
                      {user.role !== 'super_admin' && (
                        <>
                          <button
                            onClick={() => setEditingUser(user)}
                            className="text-blue-600 hover:text-blue-900"
                          >
                            Edit
                          </button>
                          {user.is_active && (
                            <button
                              onClick={() => handleDeactivate(user.id, user.email)}
                              className="text-red-600 hover:text-red-900"
                            >
                              Deactivate
                            </button>
                          )}
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {users.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              No users found. Invite an admin to get started.
            </div>
          )}
        </div>
      )}

      {/* Modals */}
      <InviteUserModal isOpen={isInviteModalOpen} onClose={() => setIsInviteModalOpen(false)} />
      <EditPermissionsDrawer
        user={editingUser}
        isOpen={!!editingUser}
        onClose={() => setEditingUser(null)}
      />
    </div>
  );
}
