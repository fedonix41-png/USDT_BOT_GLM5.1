import { create } from "zustand";
import { AuthState, UserProfile, ExchangeOrder, SystemSettings } from "../types";

// Telegram SDK Helper for Haptic Feedback
export const triggerHaptic = {
  light: (addLog: (text: string, type: "light" | "success" | "error") => void) => {
    addLog("Вибрация: WebApp.HapticFeedback.impactOccurred('light')", "light");
    if (window.Telegram?.WebApp?.HapticFeedback) {
      try {
        window.Telegram.WebApp.HapticFeedback.impactOccurred("light");
      } catch (e) {
        console.warn("Haptic failed", e);
      }
    }
  },
  success: (addLog: (text: string, type: "light" | "success" | "error") => void) => {
    addLog("Вибрация: WebApp.HapticFeedback.notificationOccurred('success')", "success");
    if (window.Telegram?.WebApp?.HapticFeedback) {
      try {
        window.Telegram.WebApp.HapticFeedback.notificationOccurred("success");
      } catch (e) {
        console.warn("Haptic failed", e);
      }
    }
  },
  error: (addLog: (text: string, type: "light" | "success" | "error") => void) => {
    addLog("Вибрация: WebApp.HapticFeedback.notificationOccurred('error')", "error");
    if (window.Telegram?.WebApp?.HapticFeedback) {
      try {
        window.Telegram.WebApp.HapticFeedback.notificationOccurred("warning");
      } catch (e) {
        console.warn("Haptic failed", e);
      }
    }
  }
};

export const useAuthStore = create<AuthState>((set, get) => ({
  token: null,
  user: null,
  isAuthenticated: false,
  isLoading: true,
  orders: [],
  settings: null,
  hapticLogs: [],

  setAuth: (token, user) => set({ token, user, isAuthenticated: true, isLoading: false }),
  logout: () => set({ token: null, user: null, isAuthenticated: false, isLoading: false, orders: [] }),
  setLoading: (status) => set({ isLoading: status }),
  setOrders: (orders) => set({ orders }),
  setSettings: (settings) => set({ settings }),
  
  addHapticLog: (text, type) => {
    set((state) => ({
      hapticLogs: [
        { text, time: new Date().toLocaleTimeString(), type },
        ...state.hapticLogs.slice(0, 19)
      ]
    }));
  },
  
  clearHapticLogs: () => set({ hapticLogs: [] }),
  
  updateUserBalance: (newBalance) => {
    set((state) => {
      if (!state.user) return state;
      return { user: { ...state.user, balance: newBalance } };
    });
  },

  refreshUserData: async () => {
    try {
      const responseProfile = await fetch("/api/v1/user/profile");
      if (responseProfile.ok) {
        const user = await responseProfile.json();
        if (user) {
          set({ user });
        }
      }
      
      const responseSettings = await fetch("/api/v1/exchange/settings");
      if (responseSettings.ok) {
        const settings = await responseSettings.json();
        set({ settings });
      }

      const responseOrders = await fetch("/api/v1/exchange/orders");
      if (responseOrders.ok) {
        const orders = await responseOrders.json();
        set({ orders });
      }
    } catch (e) {
      console.error("Ошибка обновления данных пользователя:", e);
    }
  }
}));
