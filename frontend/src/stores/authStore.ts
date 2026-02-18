/**
 * Authentication store using Zustand.
 * Persists token and factory to sessionStorage (tab-scoped).
 */
import { create } from 'zustand';
import type { User, Factory } from '../types';

interface AuthState {
  user: User | null;
  factory: Factory | null;
  token: string | null;
  isAuthenticated: boolean;
  setAuth: (token: string, user: User, factory: Factory) => void;
  logout: () => void;
  initAuth: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  factory: null,
  token: null,
  isAuthenticated: false,

  setAuth: (token, user, factory) => {
    // Persist to sessionStorage (tab-scoped, not localStorage)
    sessionStorage.setItem(
      'auth',
      JSON.stringify({ token, user, factory })
    );

    set({
      token,
      user,
      factory,
      isAuthenticated: true,
    });
  },

  logout: () => {
    // Clear sessionStorage
    sessionStorage.removeItem('auth');
    sessionStorage.removeItem('selectedFactory');

    set({
      user: null,
      factory: null,
      token: null,
      isAuthenticated: false,
    });
  },

  initAuth: () => {
    // Load from sessionStorage on app init
    const authData = sessionStorage.getItem('auth');
    if (authData) {
      try {
        const { token, user, factory } = JSON.parse(authData);
        set({
          token,
          user,
          factory,
          isAuthenticated: true,
        });
      } catch (error) {
        console.error('Failed to parse auth data:', error);
        sessionStorage.removeItem('auth');
      }
    }
  },
}));
