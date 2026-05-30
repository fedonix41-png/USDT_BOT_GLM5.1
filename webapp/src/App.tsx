import { useEffect, useState } from "react";
import { useAuthStore } from "./store/useAuthStore";
import UserDashboard from "./components/user/UserDashboard";
import AdminDashboard from "./components/admin/AdminDashboard";
import LoadingSkeleton from "./components/shared/LoadingSkeleton";
import { api } from "./api/client";
import type { ToastMessage } from "./types";
import { X, Bell } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";

declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        ready: () => void;
        expand: () => void;
        initData: string;
        HapticFeedback?: {
          impactOccurred: (style: "light" | "medium" | "heavy" | "rigid" | "soft") => void;
          notificationOccurred: (type: "error" | "success" | "warning") => void;
        };
        showScanQrPopup: (params: { text?: string }, callback: (text: string) => void) => void;
      };
    };
  }
}

export default function App() {
  const {
    isAuthenticated,
    user,
    isLoading,
    settings,
    setAuth,
    setLoading,
    refreshUserData,
  } = useAuthStore();

  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const showToast = (text: string, type: "success" | "error" | "info") => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, text, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  };

  const executeLogin = async () => {
    setLoading(true);
    const tgInitData = window.Telegram?.WebApp?.initData;

    try {
      const data = await api.verifyTelegram(tgInitData ?? "");
      setAuth(data.token, data.user);
      await refreshUserData();
      showToast(`Авторизован как @${data.user.username} (${data.user.role})`, "success");
    } catch (e) {
      console.error(e);
      showToast("Ошибка авторизации. Сервер вернул ошибку.", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (window.Telegram?.WebApp) {
      try {
        window.Telegram.WebApp.ready();
        window.Telegram.WebApp.expand();
      } catch (e) {
        console.warn("Telegram WebApp initialization error:", e);
      }
    }

    executeLogin();
  }, []);

  return (
    <div className="min-h-screen bg-[#0B0E14] text-white flex flex-col md:flex-row font-sans selection:bg-[#00D09E]/20 overflow-hidden">

      <div className="flex-1 flex flex-col items-center justify-start min-h-screen relative overflow-y-auto pt-4 md:pt-8 bg-radial from-[#121622] to-[#0B0E14] z-10 w-full">

        <div className="w-full max-w-md bg-[#0C1017]/90 border-0 md:border md:border-gray-800/40 md:rounded-[40px] md:shadow-[0_0_80px_rgba(0,0,0,0.8)] overflow-hidden flex flex-col min-h-screen md:min-h-[92vh] max-h-none md:max-h-[92vh] relative">

          {isLoading ? (
            <LoadingSkeleton />
          ) : !isAuthenticated ? (
            <div className="flex-1 flex flex-col justify-center items-center p-8 space-y-4 text-center">
              <div className="w-16 h-16 rounded-3xl bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-500 text-2xl animate-bounce">
                ⚠️
              </div>
              <h2 className="text-xl font-black text-white">Ошибка Аутентификации</h2>
              <p className="text-xs text-[#8E9AA7] px-4 leading-normal">
                Пожалуйста, запустите Mini App через официального Telegram бота или обновите сессию в панели разработчика.
              </p>
              <button
                onClick={() => executeLogin()}
                className="px-6 py-2.5 rounded-xl bg-[#00D09E] text-gray-950 font-extrabold text-xs tracking-wider uppercase active:scale-95 transition-transform"
              >
                Повторить Вход
              </button>
            </div>
          ) : settings && !settings.botEnabled && user?.role === "client" ? (
            <div className="flex-1 flex flex-col justify-center items-center p-8 space-y-4 text-center">
              <div className="w-16 h-16 rounded-full bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-500 text-3xl animate-pulse">
                🛑
              </div>
              <h2 className="text-lg font-black text-white">Бот временно недоступен.</h2>
              <p className="text-xs text-[#8E9AA7] px-4">
                В данный момент проводятся технические работы. Пожалуйста, зайдите позже.
              </p>
            </div>
          ) : user?.role === "client" ? (
            <UserDashboard onOrderCreated={() => showToast("Заявка успешно создана!", "success")} />
          ) : (
            <AdminDashboard />
          )}

        </div>

      </div>

      <div className="fixed top-4 right-4 z-50 space-y-2 max-w-sm">
        <AnimatePresence>
          {toasts.map((toast) => (
            <motion.div
              key={toast.id}
              initial={{ x: 50, opacity: 0, scale: 0.9 }}
              animate={{ x: 0, opacity: 1, scale: 1 }}
              exit={{ x: 50, opacity: 0, scale: 0.9 }}
              className={`p-3.5 rounded-2xl border text-xs shadow-2xl flex items-center justify-between gap-3 text-white ${
                toast.type === "success"
                  ? "bg-[#161B26] border-[#00D09E]/20"
                  : toast.type === "error"
                    ? "bg-[#161B26] border-red-500/20"
                    : "bg-[#161B26]"
              }`}
            >
              <div className="flex items-center gap-2">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                  toast.type === "success"
                    ? "bg-[#00D09E]/10 text-[#00D09E]"
                    : toast.type === "error"
                      ? "bg-red-500/10 text-red-500"
                      : "bg-gray-800 text-[#8E9AA7]"
                }`}>
                  <Bell className="w-4 h-4" />
                </div>
                <span>{toast.text}</span>
              </div>
              <button
                onClick={() => setToasts((prev) => prev.filter((t) => t.id !== toast.id))}
                className="text-gray-500 hover:text-white shrink-0"
              >
                <X className="w-4 h-4" />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

    </div>
  );
}
