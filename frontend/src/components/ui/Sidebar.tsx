/**
 * Sidebar navigation component.
 */
import { Link, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { useUIStore } from '../../stores/uiStore';
import { useLogout } from '../../hooks/useAuth';

export default function Sidebar() {
  const location = useLocation();
  const factory = useAuthStore((state) => state.factory);
  const user = useAuthStore((state) => state.user);
  const sidebarOpen = useUIStore((state) => state.sidebarOpen);
  const setSidebarOpen = useUIStore((state) => state.setSidebarOpen);
  const logout = useLogout();

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: '📊' },
    { name: 'Machines', href: '/machines', icon: '⚙️' },
    { name: 'Rules', href: '/rules', icon: '📋' },
    { name: 'Analytics', href: '/analytics', icon: '📈' },
    { name: 'Reports', href: '/reports', icon: '📄' },
  ];

  // Add Users link only for super_admin
  if (user?.role === 'super_admin') {
    navigation.push({ name: 'Users', href: '/users', icon: '👥' });
  }

  const isActive = (href: string) => {
    return location.pathname === href || location.pathname.startsWith(href + '/');
  };

  return (
    <aside
      className={`
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        lg:translate-x-0
        fixed lg:static inset-y-0 left-0 z-30
        w-64 bg-gray-900 text-white
        transform transition-transform duration-200 ease-in-out
        flex flex-col
      `}
    >
      {/* Factory name */}
      <div className="p-6 border-b border-gray-800">
        <h1 className="text-xl font-bold">{factory?.name || 'FactoryOps'}</h1>
        <p className="text-sm text-gray-400 mt-1">{factory?.slug}</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 py-6 space-y-2 overflow-y-auto">
        {navigation.map((item) => (
          <Link
            key={item.name}
            to={item.href}
            className={`
              flex items-center px-4 py-3 rounded-lg transition-colors
              ${
                isActive(item.href)
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              }
            `}
            onClick={() => {
              // Close sidebar on mobile after navigation
              if (window.innerWidth < 1024) {
                setSidebarOpen(false);
              }
            }}
          >
            <span className="text-xl mr-3">{item.icon}</span>
            <span className="font-medium">{item.name}</span>
          </Link>
        ))}
      </nav>

      {/* User info and logout */}
      <div className="p-4 border-t border-gray-800">
        <div className="mb-3">
          <p className="text-sm font-medium text-white">{user?.email}</p>
          <span
            className={`
              inline-block mt-1 px-2 py-1 text-xs font-semibold rounded
              ${
                user?.role === 'super_admin'
                  ? 'bg-purple-600 text-white'
                  : 'bg-blue-600 text-white'
              }
            `}
          >
            {user?.role === 'super_admin' ? 'Super Admin' : 'Admin'}
          </span>
        </div>
        <button
          onClick={logout}
          className="w-full px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
        >
          Logout
        </button>
      </div>
    </aside>
  );
}
