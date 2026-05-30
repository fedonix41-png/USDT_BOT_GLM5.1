import { create } from 'zustand';
import type { UserProfile, ExchangeOrder, SystemSettings } from '../types';

interface AuthState {
  token: string | null;
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  orders: ExchangeOrder[];
  settings: SystemSettings | null;
  setAuth: (token: string, user: UserProfile) => void;
  logout: () => void;
  setLoading: (status: boolean) => void;
  setOrders: (orders: ExchangeOrder[]) => void;
  setSettings: (settings: SystemSettings) => void;
  updateUserBalance: (newBalance: number) => void;
  refreshUserData: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: localStorage.getItem('token'),
  user: null,
  isAuthenticated: false,
  isLoading: true,
  orders: [],
  settings: null,

  setAuth: (token: string, user: UserProfile) => {
    localStorage.setItem('token', token);
    set({ token, user, isAuthenticated: true });
  },

  logout: () => {
    localStorage.removeItem('token');
    set({ token: null, user: null, isAuthenticated: false, orders: [], settings: null });
  },

  setLoading: (status: boolean) => set({ isLoading: status }),

  setOrders: (orders: ExchangeOrder[]) => set({ orders }),

  setSettings: (settings: SystemSettings) => set({ settings }),

  updateUserBalance: (newBalance: number) => {
    const { user } = get();
    if (user) {
      set({ user: { ...user, balance: newBalance } });
    }
  },

  refreshUserData: async () => {
    const { token } = get();
    if (!token) return;

    try {
      const response = await fetch('/api/v1/user/profile', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const user = await response.json();
        set({ user });
      }
    } catch (error) {
      console.error('Failed to refresh user data:', error);
    }
  },
}));
