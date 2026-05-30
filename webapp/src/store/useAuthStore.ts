import { create } from "zustand";
import type { AuthState } from "../types";
import { api } from "../api/client";

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

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  user: null,
  isAuthenticated: false,
  isLoading: true,
  orders: [],
  settings: null,
  tickets: [],
  hapticLogs: [],

  setAuth: (token, user) => set({ token, user, isAuthenticated: true, isLoading: false }),
  logout: () => set({ token: null, user: null, isAuthenticated: false, isLoading: false, orders: [], tickets: [] }),
  setLoading: (status) => set({ isLoading: status }),
  setOrders: (orders) => set({ orders }),
  setSettings: (settings) => set({ settings }),
  setTickets: (tickets) => set({ tickets }),

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
      const [profileResult, settingsResult, ordersResult] = await Promise.allSettled([
        api.getProfile(),
        api.getExchangeSettings(),
        api.getUserOrders(),
      ]);

      if (profileResult.status === "fulfilled") {
        set({ user: profileResult.value });
      }

      if (settingsResult.status === "fulfilled") {
        set({ settings: settingsResult.value });
      }

      if (ordersResult.status === "fulfilled") {
        set({ orders: ordersResult.value.items });
      }
    } catch (e) {
      console.error("Ошибка обновления данных пользователя:", e);
    }
  }
}));
