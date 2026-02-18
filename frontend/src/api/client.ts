/**
 * Axios client with authentication interceptors.
 */
import axios, { AxiosError } from 'axios';

// Create axios instance
export const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: Add Authorization header
api.interceptors.request.use(
  (config) => {
    // Get token from sessionStorage
    const authData = sessionStorage.getItem('auth');
    if (authData) {
      try {
        const { token } = JSON.parse(authData);
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      } catch (error) {
        console.error('Failed to parse auth data:', error);
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor: Handle 401 errors
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error: AxiosError) => {
    // Handle 401 Unauthorized
    if (error.response?.status === 401) {
      // Clear auth data
      sessionStorage.removeItem('auth');
      sessionStorage.removeItem('selectedFactory');
      
      // Redirect to login
      window.location.href = '/login';
    }
    
    // Normalize error shape
    const normalizedError = {
      message: error.response?.data?.error?.message || error.message || 'An error occurred',
      code: error.response?.data?.error?.code || 'UNKNOWN_ERROR',
      status: error.response?.status,
      details: error.response?.data?.error?.details,
    };
    
    return Promise.reject(normalizedError);
  }
);

export default api;
