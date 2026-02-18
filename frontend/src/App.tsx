import { useEffect } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './stores/authStore';
import FactorySelectPage from './pages/FactorySelect';
import LoginPage from './pages/Login';
import DashboardPage from './pages/Dashboard';
import MachinesPage from './pages/Machines';
import DeviceDetailPage from './pages/DeviceDetail';
import RulesPage from './pages/Rules';
import RuleBuilderPage from './pages/RuleBuilder';
import AnalyticsPage from './pages/Analytics';
import ReportsPage from './pages/Reports';
import MainLayout from './components/ui/MainLayout';

// Create QueryClient
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// Protected Route Component
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

// Super Admin Route Component
const SuperAdminRoute = ({ children }: { children: React.ReactNode }) => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const user = useAuthStore((state) => state.user);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (user?.role !== 'super_admin') {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
};

function App() {
  const initAuth = useAuthStore((state) => state.initAuth);

  // Initialize auth from sessionStorage on mount
  useEffect(() => {
    initAuth();
  }, [initAuth]);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/" element={<Navigate to="/factory-select" replace />} />
          <Route path="/factory-select" element={<FactorySelectPage />} />
          <Route path="/login" element={<LoginPage />} />

          {/* Protected routes with layout */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <MainLayout />
              </ProtectedRoute>
            }
          >
            <Route path="dashboard" element={<DashboardPage />} />
            {/* Machines routes */}
            <Route path="machines" element={<MachinesPage />} />
            <Route path="machines/:deviceId" element={<DeviceDetailPage />} />
            {/* Rules routes */}
            <Route path="rules" element={<RulesPage />} />
            <Route path="rules/new" element={<RuleBuilderPage />} />
            <Route path="rules/:ruleId" element={<RuleBuilderPage />} />
            {/* Analytics and Reports routes */}
            <Route path="analytics" element={<AnalyticsPage />} />
            <Route path="reports" element={<ReportsPage />} />
            
            {/* Super admin only */}
            <Route
              path="users"
              element={
                <SuperAdminRoute>
                  <div className="p-6">Users Page</div>
                </SuperAdminRoute>
              }
            />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
