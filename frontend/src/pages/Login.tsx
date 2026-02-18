/**
 * Login page.
 * Users enter credentials for the selected factory.
 */
import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useLogin } from '../hooks/useAuth';
import { useUIStore } from '../stores/uiStore';
import type { Factory } from '../types';

export default function LoginPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [factory, setFactory] = useState<Factory | null>(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const login = useLogin();
  const addNotification = useUIStore((state) => state.addNotification);

  useEffect(() => {
    // Load factory from sessionStorage
    const factoryData = sessionStorage.getItem('selectedFactory');
    if (!factoryData) {
      navigate('/factory-select');
      return;
    }

    try {
      const parsedFactory = JSON.parse(factoryData);
      setFactory(parsedFactory);
    } catch (error) {
      navigate('/factory-select');
    }
  }, [navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!factory) {
      navigate('/factory-select');
      return;
    }

    login.mutate(
      {
        factory_id: factory.id,
        email,
        password,
      },
      {
        onSuccess: () => {
          addNotification({
            type: 'success',
            title: 'Login successful',
            message: `Welcome to ${factory.name}`,
          });
          navigate('/dashboard');
        },
        onError: (error: any) => {
          addNotification({
            type: 'error',
            title: 'Login failed',
            message: error.message || 'Invalid email or password',
          });
        },
      }
    );
  };

  if (!factory) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-4">
      <div className="max-w-md w-full">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">FactoryOps</h1>
          <p className="text-gray-600">Logging into <span className="font-semibold">{factory.name}</span></p>
        </div>

        <div className="bg-white p-8 rounded-lg shadow-md">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="admin@example.com"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="••••••••"
              />
            </div>

            <button
              type="submit"
              disabled={login.isPending}
              className="w-full py-2 px-4 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {login.isPending ? 'Logging in...' : 'Login'}
            </button>
          </form>

          <div className="mt-6 text-center">
            <Link
              to="/factory-select"
              className="text-sm text-blue-600 hover:text-blue-500"
            >
              ← Back to factory selection
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
