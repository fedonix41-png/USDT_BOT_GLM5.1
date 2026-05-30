import { useEffect, useState } from "react";
import { useAuthStore, triggerHaptic } from "./store/useAuthStore";
import UserDashboard from "./components/user/UserDashboard";
import AdminDashboard from "./components/admin/AdminDashboard";
import LoadingSkeleton from "./components/shared/LoadingSkeleton";
import { api } from "./api/client";
import type { ToastMessage, UserRole } from "./types";
import {
  X,
  Bell,
  Coins,
  Layers,
  Cpu,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
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

const isDevMode = () => !window.Telegram?.WebApp?.initData;

export default function App() {
  const {
    isAuthenticated,
    user,
    isLoading,
    settings,
    setAuth,
    setLoading,
    refreshUserData,
    addHapticLog,
  } = useAuthStore();

  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const [devBarOpen, setDevBarOpen] = useState(true);
  const [simulatedRole, setSimulatedRole] = useState<UserRole>("super_admin");
  const [faucetAmount, setFaucetAmount] = useState("500.00");
  const [isDepositing, setIsDepositing] = useState(false);
  const devMode = isDevMode();

  const showToast = (text: string, type: ToastMessage["type"] | "deposit") => {
    const id = Math.random().toString(36).substring(2, 9);
    const normalizedType: ToastMessage["type"] = type === "deposit" ? "success" : type;
    setToasts((prev) => [...prev, { id, text, type: normalizedType }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  };

  const executeLogin = async (roleOverride?: UserRole) => {
    setLoading(true);
    const tgInitData = window.Telegram?.WebApp?.initData;

    try {
      const data = await api.verifyTelegram(tgInitData ?? "");
      setAuth(data.token, data.user);
      await refreshUserData();
      if (roleOverride) {
        setSimulatedRole(roleOverride);
      } else {
        setSimulatedRole(data.user.role);
      }
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

  const triggerFaucetDeposit = async () => {
    if (!user) return;
    setIsDepositing(true);
    triggerHaptic.light(addHapticLog);

    const amountNum = parseFloat(faucetAmount);
    if (isNaN(amountNum) || amountNum <= 0) {
      showToast("Введите корректную сумму", "info");
      setIsDepositing(false);
      return;
    }

    try {
      await api.updateUser(user.id, {
        balance: Number((user.balance + amountNum).toFixed(2)),
      });

      useAuthStore.getState().updateUserBalance(Number((user.balance + amountNum).toFixed(2)));
      await refreshUserData();

      triggerHaptic.success(addHapticLog);
      showToast(`Баланс пополнен на +${amountNum.toFixed(2)} USDT!`, "deposit");
    } catch (e) {
      console.error(e);
      showToast("Ошибка при начислении депозита", "error");
    } finally {
      setIsDepositing(false);
    }
  };

  const handleDevRoleSwitch = async (targetRole: UserRole) => {
    if (!user) return;
    triggerHaptic.success(addHapticLog);
    try {
      await api.updateUserRole(user.id, targetRole);
      setSimulatedRole(targetRole);
      await refreshUserData();
      showToast(`Роль изменена на ${targetRole}`, "success");
    } catch (e) {
      console.error(e);
      showToast("Ошибка смены роли", "error");
    }
  };

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
                id="btn-app-retry-login"
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

      {devMode && (
        <div className="w-full md:w-96 bg-[#161B26] border-t md:border-t-0 md:border-l border-gray-800/80 p-5 flex flex-col justify-between relative z-30 font-sans shadow-2xl shrink-0 overflow-y-auto md:max-h-screen">

          <div className="space-y-4">

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#00D09E] animate-ping" />
                <Cpu className="w-5 h-5 text-[#00D09E]" />
                <h3 className="text-sm font-extrabold text-white uppercase tracking-wider">Панель Разработчика (Песочница)</h3>
              </div>

              <button
                id="btn-toggle-dev-panel"
                onClick={() => {
                  triggerHaptic.light(addHapticLog);
                  setDevBarOpen(!devBarOpen);
                }}
                className="p-1 rounded bg-[#0B0E14] text-[#8E9AA7]"
              >
                {devBarOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>
            </div>

            <p className="text-[11px] text-[#8E9AA7] leading-relaxed">
              Интерактивный пульт для тестирования логики обменного бота USDT ↔ RUB (купить/продать). Переключайте роли для проверки матрицы прав.
            </p>

            <AnimatePresence>
              {devBarOpen && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="space-y-4.5 overflow-hidden pt-1"
                >
                  <div className="space-y-2 bg-[#0B0E14] border border-gray-850 p-3.5 rounded-2xl">
                    <span className="text-[10px] text-[#8E9AA7] uppercase font-bold flex items-center gap-1.5">
                      <Layers className="w-3.5 h-3.5 text-[#00D09E]" />
                      Переключить RBAC роль:
                    </span>

                    <div className="grid grid-cols-2 gap-1.5 pt-1">
                      {(["client", "operator", "admin", "super_admin"] as const).map((rl) => (
                        <button
                          key={rl}
                          id={`btn-dev-role-${rl}`}
                          onClick={() => handleDevRoleSwitch(rl)}
                          disabled={!user}
                          className={`py-2 text-[10px] uppercase font-bold rounded-xl transition-all ${
                            simulatedRole === rl
                              ? "bg-[#00D09E] text-gray-950 font-black shadow-lg shadow-[#00D09E]/10"
                              : "bg-[#161B26] border border-gray-800 text-[#8E9AA7] hover:text-white"
                          } disabled:opacity-40`}
                        >
                          {rl === "client" ? "client (ур. 1)" : rl === "operator" ? "operator (ур. 2)" : rl === "admin" ? "admin (ур. 3)" : "super admin"}
                        </button>
                      ))}
                    </div>

                    <span className="text-[9px] text-[#8E9AA7]/85 block leading-tight pt-1">
                      * Смена роли обновляет RBAC-привилегии через API бота и обновляет интерфейс.
                    </span>
                  </div>

                  <div className="space-y-3 bg-[#0B0E14] border border-gray-850 p-3.5 rounded-2xl">
                    <span className="text-[10px] text-[#8E9AA7] uppercase font-bold flex items-center gap-1.5">
                      <Coins className="w-3.5 h-3.5 text-[#00D09E]" />
                      Начислить баланс USDT (для продажи):
                    </span>

                    <div className="grid grid-cols-1 gap-2">
                      <div className="space-y-1">
                        <span className="text-[9px] text-gray-500 uppercase font-black">Количество USDT</span>
                        <input
                          type="number"
                          id="dev-faucet-amount"
                          value={faucetAmount}
                          onChange={(e) => setFaucetAmount(e.target.value)}
                          className="w-full text-xs bg-[#161B26] border border-gray-800 rounded-xl p-2.5 font-bold text-white focus:outline-none focus:border-[#00D09E]"
                        />
                      </div>
                    </div>

                    <button
                      id="btn-dev-deposit-trigger"
                      onClick={triggerFaucetDeposit}
                      disabled={isDepositing || !user}
                      className="w-full py-3 rounded-xl bg-[#00D09E]/10 border border-[#00D09E]/30 text-[#00D09E] text-xs font-bold hover:bg-[#00D09E]/20 active:scale-[0.99] transition-transform flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-40"
                    >
                      {isDepositing ? (
                        <span>Начисление...</span>
                      ) : (
                        <>
                          <Coins className="w-3.5 h-3.5" />
                          <span>Начислить {faucetAmount} USDT на баланс</span>
                        </>
                      )}
                    </button>

                    <span className="text-[9px] text-[#8E9AA7]/85 block leading-tight">
                      * Это обновит баланс текущей сессии через API бота, вы сможете протестировать продажу USDT за Рубли.
                    </span>
                  </div>

                  <div className="space-y-2 bg-[#0B0E14] border border-gray-850 p-3 rounded-2xl">
                    <div className="flex justify-between items-center text-[10px] text-[#8E9AA7] uppercase font-bold">
                      <span>Телеметрия Haptics (Последний):</span>
                      <span className="text-gray-500">Live</span>
                    </div>
                    <div className="bg-[#161B26] border border-gray-800 text-[10px] font-mono p-2.5 rounded-xl text-gray-400 min-h-11">
                      {useAuthStore.getState().hapticLogs?.[0] ? (
                        <span className={useAuthStore.getState().hapticLogs[0].type === "success" ? "text-[#00D09E]" : "text-white"}>
                          [{useAuthStore.getState().hapticLogs[0].time}] {useAuthStore.getState().hapticLogs[0].text}
                        </span>
                      ) : (
                        <span className="text-gray-600">Логи тактильного отклика пусты...</span>
                      )}
                    </div>
                  </div>

                </motion.div>
              )}
            </AnimatePresence>

          </div>

          <div className="mt-6 pt-4 border-t border-gray-800/60 hidden md:block text-center">
            <span className="text-[10px] font-mono text-gray-650 tracking-wider">TELEPAY EXCHANGE TMA v6 • DEV SANDBOX</span>
          </div>

        </div>
      )}

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
                  {toast.type === "success" ? <Coins className="w-4 h-4 animate-bounce" /> : <Bell className="w-4 h-4" />}
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
