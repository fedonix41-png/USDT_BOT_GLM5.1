import { useState, useEffect } from "react";
import { useAuthStore, triggerHaptic } from "../../store/useAuthStore";
import { ExchangeOrder, SupportTicket } from "../../types";
import { api } from "../../api/client";
import QrCodeGenerator from "../shared/QrCodeGenerator";
import { 
  Plus, 
  ArrowUpRight, 
  ArrowDownLeft, 
  Copy, 
  Check, 
  Clock, 
  Users, 
  Wallet, 
  Info, 
  HelpCircle,
  TrendingUp,
  Shield,
  AlertTriangle,
  RefreshCw,
  X,
  CreditCard,
  MessageSquare,
  ArrowRightLeft,
  Award,
  ChevronRight,
  Send,
  MessageCircle
} from "lucide-react";
import { motion, AnimatePresence } from "motion/react";

interface UserDashboardProps {
  onOrderCreated?: () => void;
}

const sparklineData = {
  "1D": [93.10, 93.45, 93.20, 93.65, 94.12, 93.90, 94.35, 94.50],
  "1W": [91.80, 92.40, 92.15, 93.05, 92.80, 93.60, 94.10, 94.50],
  "1M": [89.50, 90.20, 91.10, 90.75, 92.30, 93.12, 93.80, 94.50]
};

export default function UserDashboard({ onOrderCreated }: UserDashboardProps) {
  const { user, orders, settings, addHapticLog, refreshUserData } = useAuthStore();
  const [activeTab, setActiveTab] = useState<"exchange" | "history" | "profile" | "referrals" | "support">("exchange");
  
  const MIN_EXCHANGE_LIMIT_USDT = 10;
  const [exchangeType, setExchangeType] = useState<"buy" | "sell">("buy");
  const [usdtAmount, setUsdtAmount] = useState("100");
  const [rubAmount, setRubAmount] = useState("");
  const [clientDetails, setClientDetails] = useState("");
  
  const [userLevel, setUserLevel] = useState<"standard" | "gold">(() => {
    return (localStorage.getItem("telepay_user_level") as "standard" | "gold") || "standard";
  });
  const [savedCard, setSavedCard] = useState(() => {
    return localStorage.getItem("telepay_preset_card") || "";
  });
  const [savedWallet, setSavedWallet] = useState(() => {
    return localStorage.getItem("telepay_preset_wallet") || "";
  });

  const [kycProgress, setKycProgress] = useState<number>(() => {
    const saved = localStorage.getItem("telepay_kyc_progress");
    return saved ? parseInt(saved) : 35;
  });
  const [fioInput, setFioInput] = useState("");
  const [phoneInput, setPhoneInput] = useState("");
  const [isKycModalOpen, setIsKycModalOpen] = useState(false);
  const [kycSuccessMessage, setKycSuccessMessage] = useState("");
  const [kycIsSubmitting, setKycIsSubmitting] = useState(false);

  const [activeChartPeriod, setActiveChartPeriod] = useState<"1D" | "1W" | "1M">("1D");
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [submitSuccess, setSubmitSuccess] = useState("");
  const [copiedType, setCopiedType] = useState<string | null>(null);

  const [selectedOrder, setSelectedOrder] = useState<ExchangeOrder | null>(null);

  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [ticketsLoading, setTicketsLoading] = useState(false);
  const [activeTicketId, setActiveTicketId] = useState<number | null>(null);
  const [newTicketSubject, setNewTicketSubject] = useState("Другое");
  const [newTicketText, setNewTicketText] = useState("");
  const [newMsgText, setNewMsgText] = useState("");
  const [supportError, setSupportError] = useState("");
  const [supportSuccess, setSupportSuccess] = useState("");
  const [isOpeningForm, setIsOpeningForm] = useState(false);

  const loadTickets = async () => {
    try {
      const data = await api.getTickets();
      setTickets(data);
    } catch (e) {
      console.error(e);
    }
  };

  const handleOpenTicket = async (e: React.FormEvent) => {
    e.preventDefault();
    setSupportError("");
    setSupportSuccess("");

    if (!newTicketText.trim()) {
      setSupportError("Пожалуйста, напишите текст сообщения");
      triggerHaptic.error(addHapticLog);
      return;
    }

    try {
      const orderId = newTicketSubject.startsWith("Сделка ")
        ? parseInt(newTicketSubject.split(" ")[1]) || undefined
        : undefined;

      const ticket = await api.createTicket(newTicketSubject, orderId, newTicketText.trim());

      setSupportSuccess("Обращение успешно создано!");
      setNewTicketText("");
      setNewTicketSubject("Другое");
      setIsOpeningForm(false);
      triggerHaptic.success(addHapticLog);
      addHapticLog("Создано обращение в поддержку", "success");
      
      const freshTickets = await api.getTickets();
      setTickets(freshTickets);
      if (ticket) {
        setActiveTicketId(ticket.id);
      }
    } catch (err: any) {
      setSupportError(err?.message || "Ошибка создания обращения");
      triggerHaptic.error(addHapticLog);
    }
  };

  const handleSendTicketMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMsgText.trim() || !activeTicketId) return;

    const savedText = newMsgText;
    setNewMsgText("");

    try {
      await api.sendMessage(activeTicketId, savedText);
      triggerHaptic.light(addHapticLog);
      await loadTickets();
    } catch (e) {
      console.error(e);
      setNewMsgText(savedText);
    }
  };

  const handleCloseTicket = async (ticketId: number) => {
    try {
      await api.closeTicket(ticketId);
      triggerHaptic.success(addHapticLog);
      addHapticLog("Обращение закрыто", "success");
      await loadTickets();
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    if (activeTab === "support") {
      setTicketsLoading(true);
      loadTickets().finally(() => setTicketsLoading(false));
      
      const interval = setInterval(() => {
        loadTickets();
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [activeTab]);

  useEffect(() => {
    localStorage.setItem("telepay_user_level", userLevel);
  }, [userLevel]);

  useEffect(() => {
    localStorage.setItem("telepay_preset_card", savedCard);
  }, [savedCard]);

  useEffect(() => {
    localStorage.setItem("telepay_preset_wallet", savedWallet);
  }, [savedWallet]);

  useEffect(() => {
    localStorage.setItem("telepay_kyc_progress", kycProgress.toString());
  }, [kycProgress]);

  const isGoldActive = userLevel === "gold";
  const effectiveBuyRate = settings 
    ? (isGoldActive ? settings.buyRate - 0.45 : settings.buyRate) 
    : 0;
  const effectiveSellRate = settings 
    ? (isGoldActive ? settings.sellRate + 0.45 : settings.sellRate) 
    : 0;

  const parsedUsdt = parseFloat(usdtAmount);
  const isBelowLimit = isNaN(parsedUsdt) || parsedUsdt < MIN_EXCHANGE_LIMIT_USDT;
  const isDirectionDisabled = settings ? ((exchangeType === "buy" && !settings.buyEnabled) || (exchangeType === "sell" && !settings.sellEnabled)) : false;
  const canExchange = !isDirectionDisabled && !isBelowLimit && !isSubmitting;

  useEffect(() => {
    if (!settings) return;
    const rate = exchangeType === "buy" ? effectiveBuyRate : effectiveSellRate;
    const computedRub = (parseFloat(usdtAmount) || 0) * rate;
    setRubAmount(computedRub > 0 ? computedRub.toFixed(2) : "");
  }, [usdtAmount, exchangeType, settings, userLevel]);

  const handleRubChanged = (val: string) => {
    setRubAmount(val);
    if (!settings) return;
    const rate = exchangeType === "buy" ? effectiveBuyRate : effectiveSellRate;
    const computedUsdt = (parseFloat(val) || 0) / rate;
    setUsdtAmount(computedUsdt > 0 ? computedUsdt.toFixed(2) : "");
  };

  const copyToClipboard = (text: string, type: string) => {
    navigator.clipboard.writeText(text);
    setCopiedType(type);
    triggerHaptic.success(addHapticLog);
    setTimeout(() => setCopiedType(null), 2000);
  };

  const handleApplyCardPreset = () => {
    if (savedCard) {
      setClientDetails(savedCard);
      triggerHaptic.light(addHapticLog);
      addHapticLog("Карта из настроек заполнена", "success");
    }
  };

  const handleApplyWalletPreset = () => {
    if (savedWallet) {
      setClientDetails(savedWallet);
      triggerHaptic.light(addHapticLog);
      addHapticLog("USDT TRC20 адрес из настроек заполнен", "success");
    }
  };

  const handleExchangeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError("");
    setSubmitSuccess("");

    if (!settings) return;

    if (exchangeType === "buy" && !settings.buyEnabled) {
      setSubmitError("Покупка USDT временно приостановлена администратором.");
      triggerHaptic.error(addHapticLog);
      return;
    }

    if (exchangeType === "sell" && !settings.sellEnabled) {
      setSubmitError("Продажа USDT временно приостановлена администратором.");
      triggerHaptic.error(addHapticLog);
      return;
    }

    const usdtNum = parseFloat(usdtAmount);
    if (isNaN(usdtNum) || usdtNum <= 0) {
      setSubmitError("Укажите корректную сумму USDT (> 0)");
      triggerHaptic.error(addHapticLog);
      return;
    }

    if (usdtNum < MIN_EXCHANGE_LIMIT_USDT) {
      setSubmitError(`Сумма обмена ниже минимального лимита в ${MIN_EXCHANGE_LIMIT_USDT} USDT`);
      triggerHaptic.error(addHapticLog);
      return;
    }

    if (!clientDetails.trim()) {
      setSubmitError(
        exchangeType === "buy" 
          ? "Введите ваш внешний USDT-адрес получения" 
          : "Введите вашу банковскую карту / телефон получения RUB"
      );
      triggerHaptic.error(addHapticLog);
      return;
    }

    if (exchangeType === "sell" && user && user.balance < usdtNum) {
      setSubmitError(`Недостаточно USDT на вашем балансе. Доступно: ${user.balance} USDT`);
      triggerHaptic.error(addHapticLog);
      return;
    }

    setIsSubmitting(true);
    triggerHaptic.light(addHapticLog);

    try {
      await api.createOrder(exchangeType, usdtNum, clientDetails.trim());

      triggerHaptic.success(addHapticLog);
      setSubmitSuccess(
        exchangeType === "buy" 
          ? "Заявка на покупку создана! Переведите рубли на указанную карту и ожидайте зачисления."
          : "Заявка на продажу создана! Ожидайте поступления рублей на ваши реквизиты."
      );
      setClientDetails("");
      
      await refreshUserData();
      if (onOrderCreated) {
        onOrderCreated();
      }

      setTimeout(() => {
        setSubmitSuccess("");
        setActiveTab("history");
      }, 3000);
    } catch (err: any) {
      setSubmitError(err?.message || "Ошибка создания заявки обмена");
      triggerHaptic.error(addHapticLog);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancelOrder = async (orderId: number) => {
    triggerHaptic.light(addHapticLog);
    try {
      await api.cancelOrder(orderId);
      triggerHaptic.success(addHapticLog);
      addHapticLog(`Заявка ${orderId} отменена`, "success");
      setSelectedOrder(null);
      await refreshUserData();
    } catch (err: any) {
      alert(err?.message || "Ошибка отмены заявки");
      triggerHaptic.error(addHapticLog);
    }
  };

  const handleFileComplaint = async (orderId: number) => {
    triggerHaptic.light(addHapticLog);
    try {
      await api.complainOrder(orderId);
      triggerHaptic.success(addHapticLog);
      addHapticLog(`Претензия по заявке ${orderId} отправлена администраторам`, "success");
      setSelectedOrder(null);
      await refreshUserData();
    } catch (err: any) {
      alert(err?.message || "Ошибка отправки претензии");
      triggerHaptic.error(addHapticLog);
    }
  };

  const handleKycSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!fioInput.trim() || !phoneInput.trim()) return;
    
    setKycIsSubmitting(true);
    triggerHaptic.light(addHapticLog);
    
    setTimeout(() => {
      setKycProgress(100);
      setUserLevel("gold");
      setKycSuccessMessage("Поздравляем! Верификация одобрена в реальном времени. Статус GOLD активирован! 🎉");
      setKycIsSubmitting(false);
      triggerHaptic.success(addHapticLog);
      addHapticLog("Верификация KYC-2 успешна!", "success");
    }, 1500);
  };

  const resetKycSimulator = () => {
    setKycProgress(35);
    setUserLevel("standard");
    setFioInput("");
    setPhoneInput("");
    setKycSuccessMessage("");
    triggerHaptic.light(addHapticLog);
  };

  const currentTrendPrices = sparklineData[activeChartPeriod];
  const maxPrice = Math.max(...currentTrendPrices);
  const minPrice = Math.min(...currentTrendPrices);
  const pointsString = currentTrendPrices.map((price, idx) => {
    const x = (idx / (currentTrendPrices.length - 1)) * 340 + 10;
    const y = 60 - ((price - minPrice) / (maxPrice - minPrice || 1)) * 40;
    return `${x},${y}`;
  }).join(" ");

  return (
    <div className="flex-1 flex flex-col justify-between max-w-md mx-auto w-full relative pb-28">
      
      <div className="p-4 flex items-center justify-between border-b border-gray-800/40 bg-gradient-to-r from-[#0C1017] via-[#111622] to-[#0C1017] relative">
        <div className="absolute bottom-0 left-0 right-0 h-[1.5px] bg-gradient-to-r from-pink-500 via-amber-400 to-emerald-400 opacity-80" />
        
        <div className="flex items-center gap-2.5">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 via-amber-500 to-pink-500 p-[1px] shadow-lg shadow-pink-500/5">
            <div className="w-full h-full rounded-[11px] bg-[#0c1017] flex items-center justify-center text-emerald-400 font-extrabold text-lg">
              ⇄
            </div>
          </div>
          <div>
            <div className="flex items-center gap-1">
              <h1 className="text-sm font-black text-white tracking-wide uppercase font-mono bg-gradient-to-r from-amber-200 via-pink-300 to-emerald-300 bg-clip-text text-transparent">
                Telepay Gold
              </h1>
              <span className="text-[10px] bg-amber-400/10 text-amber-300 border border-amber-500/20 px-1 border-dotted rounded font-bold">P2P</span>
            </div>
            <span className="text-[10px] text-gray-400 block">
              @{user?.username} • client {isGoldActive ? (
                <span className="text-amber-400 font-bold">★ GOLD</span>
              ) : (
                <span className="text-[#8E9AA7]">ур. 1</span>
              )}
            </span>
          </div>
        </div>
        
        <div className="flex flex-col items-end">
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#161B26] border border-gray-800/80 text-[10px] font-bold text-emerald-400 animate-pulse">
            <Shield className="w-3.5 h-3.5 shrink-0" />
            <span>P2P Защита</span>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        
        {activeTab === "exchange" && settings && (
          <div className="space-y-4">
            
            <div className="space-y-3 bg-[#0e121a]/80 border border-white/5 rounded-3xl p-3.5 relative overflow-hidden backdrop-blur-md">
              <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-br from-emerald-500/5 via-pink-500/5 to-transparent blur-lg pointer-events-none" />
              
              <div className="grid grid-cols-2 gap-2.5 pb-2.5 border-b border-gray-850">
                <div className="bg-[#121620] border border-white/5 p-2.5 rounded-2xl relative overflow-hidden flex flex-col justify-between">
                  <span className="absolute top-2.5 right-2.5 w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  <div>
                    <span className="text-[8px] uppercase text-[#8E9AA7] font-black tracking-wider block">USDT Кошелек</span>
                    <span className="text-sm font-black text-white font-mono block mt-1">
                      ₮ {(user?.balance ?? 0).toLocaleString("ru-RU", { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                  <span className="text-[9px] text-[#8E9AA7] font-mono block mt-1 opacity-85">
                    ≈ {((user?.balance ?? 0) * effectiveSellRate).toLocaleString("ru-RU", { maximumFractionDigits: 0 })} ₽
                  </span>
                </div>

                <div className="bg-[#121620] border border-white/5 p-2.5 rounded-2xl relative overflow-hidden flex flex-col justify-between">
                  <span className="absolute top-2.5 right-2.5 w-1.5 h-1.5 rounded-full bg-pink-500" />
                  <div>
                    <span className="text-[8px] uppercase text-[#8E9AA7] font-black tracking-wider block">Фиатный счет (RUB)</span>
                    <span className="text-sm font-black text-white font-mono block mt-1 font-sans">
                      ₽ {(user?.fiatBalance ?? 0).toLocaleString("ru-RU", { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                  <span className="text-[9px] text-[#8E9AA7] font-mono block mt-1 opacity-85">
                    ≈ {((user?.fiatBalance ?? 0) / (effectiveBuyRate || 1)).toLocaleString("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ₮
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="flex items-center justify-between bg-[#161B26]/60 px-2.5 py-1.5 rounded-xl border border-gray-800/60">
                  <span className="text-[9px] text-[#8E9AA7] font-bold uppercase tracking-wider">Купить:</span>
                  <div className="flex items-center gap-1.5">
                    <span className="font-mono text-xs font-black text-white">{effectiveBuyRate.toFixed(2)} ₽</span>
                    {isGoldActive ? (
                      <span className="text-[8px] text-amber-300 font-bold bg-amber-400/10 px-1 rounded">★ -0.45</span>
                    ) : (
                      <span className="text-[8px] text-pink-400 font-bold bg-pink-400/10 px-1 rounded">стандарт</span>
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-between bg-[#161B26]/60 px-2.5 py-1.5 rounded-xl border border-gray-800/60">
                  <span className="text-[9px] text-[#8E9AA7] font-bold uppercase tracking-wider">Продать:</span>
                  <div className="flex items-center gap-1.5">
                    <span className="font-mono text-xs font-black text-emerald-400">{effectiveSellRate.toFixed(2)} ₽</span>
                    {isGoldActive ? (
                      <span className="text-[8px] text-amber-300 font-bold bg-amber-400/10 px-1 rounded">★ +0.45</span>
                    ) : (
                      <span className="text-[8px] text-gray-550 block bg-gray-800/40 px-1 rounded">-</span>
                    )}
                  </div>
                </div>
              </div>

              {!isGoldActive && (
                <div 
                  id="promo-gold-framer"
                  onClick={() => {
                    triggerHaptic.light(addHapticLog);
                    setActiveTab("profile");
                  }}
                  className="pt-1.5 flex items-center justify-between text-[9px] text-[#8E9AA7] hover:text-amber-300 cursor-pointer transition-colors"
                >
                  <span className="flex items-center gap-1 font-semibold">
                    <Award className="w-3 h-3 text-amber-400 shrink-0 animate-pulse" />
                    Хотите курс выгоднее на +0.45 руб? Активируйте Кабинет
                  </span>
                  <ChevronRight className="w-3 h-3 text-gray-550" />
                </div>
              )}
            </div>

            {submitError && (
              <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-xs p-3.5 rounded-2xl text-center font-bold flex items-center justify-center gap-2">
                <AlertTriangle className="w-4 h-4 text-red-500 shrink-0" />
                <span>{submitError}</span>
              </div>
            )}
            {submitSuccess && (
              <div className="bg-[#00D09E]/10 border border-[#00D09E]/20 text-[#00D09E] text-xs p-3.5 rounded-2xl text-center font-semibold">
                ✓ {submitSuccess}
              </div>
            )}

            <div className="bg-[#0B0E14] border border-gray-800/85 p-1 rounded-2xl grid grid-cols-2 gap-1">
              <button
                id="exchange-tab-buy"
                onClick={() => {
                  triggerHaptic.light(addHapticLog);
                  setExchangeType("buy");
                  setSubmitError("");
                }}
                className={`py-2 text-xs font-bold rounded-xl transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
                  exchangeType === "buy" 
                    ? "bg-[#161B26] border border-gray-800 text-pink-400 font-extrabold shadow-md" 
                    : "text-[#8E9AA7] hover:text-white"
                }`}
              >
                <ArrowDownLeft className="w-3.5 h-3.5" />
                <span>Купить USDT (за ₽)</span>
              </button>
              <button
                id="exchange-tab-sell"
                onClick={() => {
                  triggerHaptic.light(addHapticLog);
                  setExchangeType("sell");
                  setSubmitError("");
                }}
                className={`py-2 text-xs font-bold rounded-xl transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
                  exchangeType === "sell" 
                    ? "bg-[#161B26] border border-gray-800 text-emerald-400 font-extrabold shadow-md" 
                    : "text-[#8E9AA7] hover:text-white"
                }`}
              >
                <ArrowUpRight className="w-3.5 h-3.5" />
                <span>Продать USDT (за ₽)</span>
              </button>
            </div>

            {exchangeType === "buy" && !settings.buyEnabled && (
              <div className="bg-red-500/10 border border-red-500/20 p-4 rounded-2xl space-y-2 flex flex-col items-center text-center">
                <AlertTriangle className="w-8 h-8 text-pink-500 animate-pulse" />
                <h4 className="text-xs font-bold text-white uppercase tracking-wide">Покупка монет временно приостановлена</h4>
                <p className="text-[10px] text-gray-400 leading-relaxed max-w-[90%]">
                  Прием фиатных платежей на банковские реквизиты временно остановлен администратором для проведения инвентаризации лимитов P2P.
                </p>
              </div>
            )}

            {exchangeType === "sell" && !settings.sellEnabled && (
              <div className="bg-red-500/10 border border-red-500/20 p-4 rounded-2xl space-y-2 flex flex-col items-center text-center">
                <AlertTriangle className="w-8 h-8 text-emerald-500 animate-pulse" />
                <h4 className="text-xs font-bold text-white uppercase tracking-wide">Продажа монет временно приостановлена</h4>
                <p className="text-[10px] text-gray-400 leading-relaxed max-w-[90%]">
                  Вывод средств на банковские счета временно приостановлен в связи с техническими работами банка.
                </p>
              </div>
            )}

            <form id="form-exchange" onSubmit={handleExchangeSubmit} className="space-y-4">
                
                <div className="bg-[#0B0E14] border border-gray-800/80 p-4 rounded-2xl space-y-3.5">
                  
                  <div className="space-y-1">
                    <div className="flex justify-between items-center text-[10px] text-[#8E9AA7] uppercase font-bold">
                      <span>Сумма USDT:</span>
                      {exchangeType === "sell" && (
                        <span>Доступно: <span className="text-emerald-400 font-bold font-mono">{user?.balance} USDT</span></span>
                      )}
                    </div>
                    <div className="relative">
                      <input
                        type="number"
                        id="input-usdt-amount"
                        step="any"
                        value={usdtAmount}
                        onChange={(e) => setUsdtAmount(e.target.value)}
                        className="w-full text-sm font-bold bg-[#161B26] border border-gray-800 focus:border-pink-500/40 rounded-xl p-3 text-white focus:outline-none placeholder-gray-700 font-mono"
                        placeholder="0.00"
                        required
                      />
                      <span className="absolute right-3.5 top-3 text-xs font-bold text-emerald-400">USDT</span>
                    </div>
                  </div>

                  <div className="flex justify-center -my-1">
                    <div className="w-7 h-7 rounded-full bg-gray-800/60 flex items-center justify-center border border-gray-700/50">
                      <ArrowRightLeft className="w-3.5 h-3.5 text-pink-400 rotate-90" />
                    </div>
                  </div>

                  <div className="space-y-1">
                    <span className="text-[10px] text-[#8E9AA7] uppercase font-bold block">Сумма в рублях (RUB):</span>
                    <div className="relative">
                      <input
                        type="number"
                        id="input-rub-amount"
                        step="any"
                        value={rubAmount}
                        onChange={(e) => handleRubChanged(e.target.value)}
                        className="w-full text-sm font-bold bg-[#161B26] border border-gray-800 focus:border-amber-500/40 rounded-xl p-3 text-white focus:outline-none placeholder-gray-700 font-mono"
                        placeholder="0.00"
                        required
                      />
                      <span className="absolute right-3.5 top-3 text-xs font-bold text-amber-400">₽ (RUB)</span>
                    </div>
                  </div>
                </div>

                {usdtAmount && isBelowLimit && (
                  <div className="bg-amber-400/5 border border-amber-400/20 px-3.5 py-3 rounded-2xl flex items-start gap-2.5">
                    <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                    <div className="space-y-0.5">
                      <span className="text-[10px] text-white uppercase font-bold tracking-wider block">Сумма ниже минимального лимита</span>
                      <p className="text-[10px] text-gray-400 leading-normal">
                        Минимальный лимит обмена через бота составляет <span className="text-amber-300 font-extrabold font-mono">{MIN_EXCHANGE_LIMIT_USDT} USDT</span>. Пожалуйста, укажите большую сумму.
                      </p>
                    </div>
                  </div>
                )}

                {exchangeType === "buy" ? (
                  <div className="space-y-4">
                    <div className="space-y-1.5">
                      <div className="flex justify-between items-center text-[10px] text-[#8E9AA7] uppercase font-bold">
                        <label>Ваш внешний USDT-кошелек получения:</label>
                        {savedWallet && (
                          <button
                            type="button"
                            onClick={handleApplyWalletPreset}
                            className="text-[9px] text-amber-400 font-bold hover:underline"
                          >
                            ⚡ Вставить из Кабинета
                          </button>
                        )}
                      </div>
                      <input
                        type="text"
                        id="client-receiving-wallet"
                        placeholder="Введите ваш USDT адрес TRC-20/TON..."
                        value={clientDetails}
                        onChange={(e) => setClientDetails(e.target.value)}
                        className="w-full text-xs font-semibold bg-[#0B0E14] border border-gray-850 focus:border-pink-500/40 rounded-xl p-3 text-white placeholder-gray-600 focus:outline-none"
                      />
                    </div>

                    <div className="bg-[#161B26] border border-amber-500/10 p-4 rounded-3xl space-y-3 relative overflow-hidden">
                      <div className="absolute top-0 right-0 w-24 h-24 bg-amber-500/2 rounded-full blur-2xl pointer-events-none" />
                      
                      <div>
                        <span className="text-[10px] text-amber-400 uppercase font-black tracking-widest block">Реквизиты для оплаты (Трансфер ₽)</span>
                        <p className="text-[10px] text-[#8E9AA7] mt-0.5">Вам необходимо сделать перевод в рублях на карты банка:</p>
                      </div>

                      <div className="bg-[#0B0E14] border border-gray-850 p-3 rounded-2xl flex items-center justify-between">
                        <span className="text-[11px] font-mono font-bold text-white break-all pr-2">
                          {settings.requisitesCard}
                        </span>
                        
                        <button
                          type="button"
                          id="btn-copy-card-requisites"
                          onClick={() => copyToClipboard(settings.requisitesCard, "card_req")}
                          className="p-2 rounded-xl bg-gray-800 hover:bg-gray-750 text-[#8E9AA7] hover:text-white shrink-0 cursor-pointer border border-gray-750"
                        >
                          {copiedType === "card_req" ? (
                            <Check className="w-3.5 h-3.5 text-emerald-400" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>

                      <div className="text-[10px] text-[#8E9AA7] flex gap-2 leading-relaxed">
                        <Info className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                        <p>После отправки перевода по реквизитам Сбербанк/Т-Банк, нажмите кнопку <span className="text-white font-bold">"Купить USDT"</span> ниже. Оператор зачислит монеты сразу по приходу РУБ.</p>
                      </div>
                    </div>

                  </div>
                ) : (
                  <div className="space-y-4">
                    
                    <div className="space-y-1.5">
                      <div className="flex justify-between items-center text-[10px] text-[#8E9AA7] uppercase font-bold">
                        <label>Ваши реквизиты для получения RUB:</label>
                        {savedCard && (
                          <button
                            type="button"
                            onClick={handleApplyCardPreset}
                            className="text-[9px] text-amber-400 font-bold hover:underline"
                          >
                            ⚡ Вставить из Кабинета
                          </button>
                        )}
                      </div>
                      <input
                        type="text"
                        id="client-receiving-card"
                        placeholder="Например: Сбербанк • 2202 ... • Никита Р."
                        value={clientDetails}
                        onChange={(e) => setClientDetails(e.target.value)}
                        className="w-full text-xs font-semibold bg-[#0B0E14] border border-gray-850 focus:border-emerald-500/40 rounded-xl p-3 text-white placeholder-gray-600 focus:outline-none"
                      />
                    </div>

                    <div className="bg-[#161B26] border border-emerald-500/10 p-4 rounded-3xl space-y-3">
                      
                      <div>
                        <span className="text-[10px] text-[#8E9AA7] uppercase font-bold block">Депозитный USDT-кошелек обменника:</span>
                        <p className="text-[10px] text-[#8E9AA7] mt-0.5 leading-tight">Для проведения сделки USDT будут списаны с вашего баланса Mini App.</p>
                      </div>

                      <div className="flex flex-col items-center justify-center p-1 bg-[#121620] border border-gray-850 rounded-2xl w-24 h-24 mx-auto shadow-inner">
                        <QrCodeGenerator value={settings.requisitesWallet} size={84} />
                      </div>

                      <div className="bg-[#0B0E14] border border-gray-850 p-2.5 rounded-2xl flex items-center justify-between">
                        <span className="text-[10px] font-mono text-gray-400 break-all pr-2">
                          {settings.requisitesWallet}
                        </span>
                        <button
                          type="button"
                          id="btn-copy-wallet-requisites"
                          onClick={() => copyToClipboard(settings.requisitesWallet, "wallet_req")}
                          className="p-2 rounded-xl bg-gray-800 hover:bg-gray-750 text-[#8E9AA7] hover:text-white shrink-0 cursor-pointer border border-gray-750"
                        >
                          {copiedType === "wallet_req" ? (
                            <Check className="w-3.5 h-3.5 text-[#00D09E]" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>

                    </div>

                  </div>
                )}

                <button
                  type="submit"
                  id="btn-exchange-submit"
                  disabled={!canExchange}
                  className={`w-full py-3.5 px-4 disabled:opacity-40 disabled:cursor-not-allowed disabled:saturate-[0.35] text-gray-950 font-black rounded-2xl transition-all uppercase text-[11px] tracking-wider shadow-lg flex items-center justify-center gap-2 cursor-pointer ${
                    exchangeType === "buy" 
                      ? "bg-gradient-to-r from-pink-500 via-pink-400 to-pink-500 shadow-pink-500/10 hover-brightness" 
                      : "bg-gradient-to-r from-[#00D09E] via-[#10B981] to-[#00D09E] shadow-[#00D09E]/10"
                  }`}
                >
                  <Plus className="w-4 h-4 stroke-[3px]" />
                  <span>
                    {isSubmitting 
                      ? "Создание сделки..." 
                      : isDirectionDisabled
                        ? "Направление отключено"
                        : isBelowLimit
                          ? `Минимум: ${MIN_EXCHANGE_LIMIT_USDT} USDT`
                          : exchangeType === "buy" 
                            ? `Купить USDT за ${parseFloat(rubAmount || "0").toLocaleString("ru-RU")} RUB`
                            : `Продать USDT за ${parseFloat(rubAmount || "0").toLocaleString("ru-RU")} RUB`
                    }
                  </span>
                </button>

              </form>

          </div>
        )}

        {activeTab === "history" && (
          <div className="space-y-4">
            
            <div className="flex justify-between items-center">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Clock className="w-5 h-5 text-pink-400" />
                <span>История обменов</span>
              </h2>
              <span className="text-[10px] font-mono text-[#8E9AA7] bg-[#161B26] border border-gray-800 px-2.5 py-0.5 rounded-full">
                {orders.length} транзакций
              </span>
            </div>

            {orders.length === 0 ? (
              <div className="bg-[#161B26] border border-gray-800 p-12 rounded-3xl text-center space-y-3">
                <MessageSquare className="w-10 h-10 text-gray-700 mx-auto" />
                <p className="text-xs text-[#8E9AA7]">Вы пока не создали ни одной заявки обмена. Выберите Направление во вкладке Обмен!</p>
              </div>
            ) : (
              <div className="space-y-2.5">
                {orders.map((ord) => (
                  <div
                    key={ord.id}
                    id={`order-row-${ord.id}`}
                    onClick={() => {
                      triggerHaptic.light(addHapticLog);
                      setSelectedOrder(ord);
                    }}
                    className="flex justify-between items-center glass hover:bg-[#1d2433]/90 p-3.5 rounded-2xl cursor-pointer transition-all duration-150 shadow-md border border-white/5 relative overflow-hidden"
                  >
                    {ord.linkBroken && (
                      <div className="absolute top-0 left-0 bottom-0 w-1 bg-red-500 animate-pulse" />
                    )}

                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-xl flex items-center justify-center shadow-inner ${
                        ord.orderType === "buy" 
                          ? "bg-pink-500/10 text-pink-400" 
                          : "bg-emerald-500/10 text-emerald-400"
                      }`}>
                        {ord.orderType === "buy" ? (
                          <ArrowDownLeft className="w-5 h-5" />
                        ) : (
                          <ArrowUpRight className="w-5 h-5" />
                        )}
                      </div>
                      <div>
                        <div className="flex items-center gap-1.5">
                          <span className="text-xs font-bold text-white">
                            {ord.orderType === "buy" ? "Покупка USDT" : "Продажа USDT"}
                          </span>
                          <span className="text-[9px] bg-gray-850 text-[#8E9AA7] font-mono px-1.5 rounded">
                            #{ord.id}
                          </span>
                        </div>
                        <span className="text-[9px] text-[#8E9AA7] block">
                          {new Date(ord.createdAt).toLocaleString("ru-RU")}
                        </span>
                      </div>
                    </div>

                    <div className="text-right">
                      <span className={`text-xs font-black block ${ord.orderType === "buy" ? "text-pink-400" : "text-emerald-400"}`}>
                        {ord.orderType === "buy" ? "+" : "-"}{ord.amountUsdt.toFixed(2)} ₮
                      </span>
                      <span className={`text-[10px] flex items-center gap-1 justify-end mt-0.5 ${
                        ord.status === "completed" 
                          ? "text-emerald-400" 
                          : ord.status === "created" 
                            ? "text-amber-500 animate-pulse" 
                            : "text-red-500"
                      }`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${
                          ord.status === "completed" ? "bg-emerald-400" : ord.status === "created" ? "bg-amber-500" : "bg-red-500"
                        }`} />
                        {ord.status === "completed" && "Завершено"}
                        {ord.status === "created" && "В обработке"}
                        {ord.status === "cancelled" && "Отменено"}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === "profile" && (
          <div className="space-y-4">
            
            <div className="flex justify-between items-center">
              <h2 className="text-base font-black text-white flex items-center gap-2">
                <Award className="w-5 h-5 text-amber-400" />
                <span>Личный кабинет Клиента</span>
              </h2>
              <span className="text-[9px] bg-gradient-to-r from-amber-400 to-pink-500 text-gray-950 font-black px-2 py-0.5 rounded-full uppercase tracking-wider">
                PRO Вкладка
              </span>
            </div>

            <div className="bg-[#121620] border border-white/5 p-4 rounded-3xl relative overflow-hidden shadow-xl space-y-4.5">
              <div className="absolute top-0 left-0 w-32 h-32 bg-amber-400/5 rounded-full blur-2xl pointer-events-none" />
              <div className="absolute bottom-0 right-0 w-32 h-32 bg-pink-500/5 rounded-full blur-2xl pointer-events-none" />

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="relative">
                    <div className={`w-12 h-12 rounded-full p-[2px] ${
                      isGoldActive 
                        ? "bg-gradient-to-tr from-amber-400 via-pink-400 to-emerald-400 animate-spin-slow" 
                        : "bg-gray-800"
                    }`}>
                      <div className="w-full h-full rounded-full bg-[#121620] flex items-center justify-center font-bold text-base text-white">
                        {user?.username ? user.username.slice(0, 2).toUpperCase() : "U"}
                      </div>
                    </div>
                    {isGoldActive && (
                      <span className="absolute -bottom-1 -right-1 bg-amber-400 text-gray-950 text-[8px] font-black w-4.5 h-4.5 rounded-full flex items-center justify-center shadow">
                        ★
                      </span>
                    )}
                  </div>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-sm font-extrabold text-white">@{user?.username}</span>
                      <span className="text-[8px] bg-[#161B26] border border-gray-800 text-gray-400 px-1.5 py-0.2 rounded font-mono">
                        ID: {user?.id}
                      </span>
                    </div>
                    <span className="text-[10px] text-gray-400 block mt-0.5 uppercase tracking-wider font-semibold">
                      Статус: {isGoldActive ? (
                        <span className="text-amber-400 font-extrabold">GOLD VIP (Уровень 2)</span>
                      ) : (
                        <span className="text-[#8E9AA7]">Стандарт (Уровень 1)</span>
                      )}
                    </span>
                  </div>
                </div>

                <div className="text-right bg-black/30 p-2.5 rounded-2xl min-w-28 border border-white/5">
                  <span className="text-[8px] text-gray-400 uppercase font-black block">P2P Рейтинг</span>
                  <span className="text-xs font-black text-emerald-400 font-mono block mt-0.5">100% Успешно</span>
                  <span className="text-[9px] text-amber-400 font-bold block">★ 5.0 (VIP)</span>
                </div>
              </div>

              <div className="bg-[#161B26]/80 border border-amber-500/20 p-3 rounded-2xl flex items-center justify-between text-xs">
                <div className="space-y-0.5">
                  <span className="text-gray-400 text-[10px] uppercase font-bold block">Ваша скидка на обмен:</span>
                  <span className="text-white font-extrabold flex items-center gap-1">
                    {isGoldActive ? "Активировано: -0.45 ₽ c ликвидности" : "Обычный тариф без скидок"}
                  </span>
                </div>
                {!isGoldActive ? (
                  <button
                    id="btn-activate-gold-cabinet"
                    onClick={() => {
                      triggerHaptic.success(addHapticLog);
                      setIsKycModalOpen(true);
                    }}
                    className="py-1.5 px-3 bg-gradient-to-r from-amber-400 to-pink-500 text-gray-950 font-black text-[10px] rounded-xl hover:opacity-90 active:scale-95 transition-all cursor-pointer"
                  >
                    Активировать Gold 🚀
                  </button>
                ) : (
                  <span className="text-emerald-400 font-extrabold text-[10px] flex items-center gap-1">
                    ✓ Премиум тариф
                  </span>
                )}
              </div>

              <div className="space-y-1.5">
                <div className="flex justify-between text-[10px]">
                  <span className="text-[#8E9AA7] font-bold uppercase">Верификация аккаунта KYC:</span>
                  <span className="text-white font-mono font-bold">{kycProgress}%</span>
                </div>
                <div className="w-full bg-[#161B26] h-2 rounded-full overflow-hidden p-[1px]">
                  <div 
                    className="h-full bg-gradient-to-r from-pink-500 via-amber-400 to-emerald-400 rounded-full transition-all duration-1000"
                    style={{ width: `${kycProgress}%` }}
                  />
                </div>
                <div className="flex justify-between text-[9px] text-gray-400">
                  <span>Ур. 1: Telegram Web ✓</span>
                  {kycProgress < 100 ? (
                    <button 
                      onClick={() => {
                        triggerHaptic.light(addHapticLog);
                        setIsKycModalOpen(true);
                      }}
                      className="text-pink-400 font-bold hover:underline"
                    >
                      Пройти KYC-2 для Gold-тарифа ➔
                    </button>
                  ) : (
                    <span className="text-emerald-400 font-black uppercase">Ур. 2: Верифицирован ★</span>
                  )}
                </div>
              </div>

            </div>

            <div className="bg-[#161B26] border border-gray-800 p-4 rounded-3xl space-y-3.5">
              <div className="flex items-center gap-1.5">
                <CreditCard className="w-4 h-4 text-pink-400" />
                <h3 className="text-xs font-black text-white uppercase tracking-wider">Шаблоны быстрых реквизитов</h3>
              </div>
              <p className="text-[10px] text-[#8E9AA7] leading-relaxed">
                Сохраните ваши реквизиты здесь, чтобы не вводить их вручную при каждом обмене. Мы автоматически добавим кнопку быстрой вставки.
              </p>

              <div className="space-y-2.5">
                <div className="space-y-1">
                  <span className="text-[9px] text-[#8E9AA7] uppercase font-bold block">Привязанная карта (для получения Рублей):</span>
                  <div className="relative">
                    <input
                      type="text"
                      placeholder="Например: Сбербанк • 2202 5543... • Никита Р."
                      value={savedCard}
                      onChange={(e) => setSavedCard(e.target.value)}
                      className="w-full text-xs bg-[#0B0E14] border border-gray-850 focus:border-pink-500/40 rounded-xl p-2.5 pr-9 text-white placeholder-gray-750 focus:outline-none font-mono"
                    />
                    <div className="absolute right-3 top-3 text-[10px] text-gray-500 pointer-events-none">
                      RUB
                    </div>
                  </div>
                </div>

                <div className="space-y-1">
                  <span className="text-[9px] text-[#8E9AA7] uppercase font-bold block">Привязанный USDT TRC-20 адрес (получение монет):</span>
                  <div className="relative">
                    <input
                      type="text"
                      placeholder="Адрес кошелька TRC-20..."
                      value={savedWallet}
                      onChange={(e) => setSavedWallet(e.target.value)}
                      className="w-full text-xs bg-[#0B0E14] border border-gray-850 focus:border-emerald-500/40 rounded-xl p-2.5 pr-9 text-white placeholder-gray-750 focus:outline-none font-mono"
                    />
                    <div className="absolute right-3 top-3 text-[10px] text-gray-500 pointer-events-none">
                      USDT
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-[#0B0E14] p-2.5 rounded-2xl flex items-center justify-between text-[10px] text-gray-400">
                <span>✓ Автоматическое сохранение изменений</span>
                <span className="text-emerald-400 font-bold font-mono">Cloud-saved</span>
              </div>
            </div>

            <div className="bg-[#121620] border border-white/5 p-4 rounded-3xl space-y-3">
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-1.5">
                  <TrendingUp className="w-4 h-4 text-emerald-400 animate-pulse" />
                  <span className="text-xs font-black text-white uppercase tracking-wider">Динамика рынка USDT/RUB</span>
                </div>

                <div className="flex gap-1 bg-[#161B26] p-0.5 rounded-lg border border-gray-800">
                  {(["1D", "1W", "1M"] as const).map((period) => (
                    <button
                      key={period}
                      onClick={() => {
                        triggerHaptic.light(addHapticLog);
                        setActiveChartPeriod(period);
                      }}
                      className={`px-2 py-0.5 text-[8px] font-bold rounded-md uppercase transition-all ${
                        activeChartPeriod === period 
                          ? "bg-gradient-to-r from-pink-500 to-amber-500 text-gray-950 font-black shadow" 
                          : "text-gray-400 hover:text-white"
                      }`}
                    >
                      {period}
                    </button>
                  ))}
                </div>
              </div>

              <div className="bg-[#0B0E14] p-3 rounded-2xl border border-gray-850 relative">
                <svg className="w-full h-16 overflow-visible" viewBox="0 0 360 60">
                  <defs>
                    <linearGradient id="chart-grad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#EC4899" stopOpacity="0.25" />
                      <stop offset="100%" stopColor="#EAB308" stopOpacity="0.01" />
                    </linearGradient>
                  </defs>
                  
                  <path 
                    d={`M 10,60 L 10,${60 - ((currentTrendPrices[0] - minPrice) / (maxPrice - minPrice)) * 40} L ${pointsString} L 350,60 Z`} 
                    fill="url(#chart-grad)"
                    className="transition-all duration-300"
                  />

                  <path 
                    d={`M ${pointsString}`} 
                    fill="none" 
                    stroke="url(#line-grad-color)" 
                    strokeWidth="2.5" 
                    strokeLinecap="round"
                    className="transition-all duration-300"
                  />
                  
                  <linearGradient id="line-grad-color" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor="#EC4899" />
                    <stop offset="50%" stopColor="#EAB308" />
                    <stop offset="100%" stopColor="#10B981" />
                  </linearGradient>

                  <circle 
                    cx="350" 
                    cy={60 - ((currentTrendPrices[currentTrendPrices.length - 1] - minPrice) / (maxPrice - minPrice)) * 40} 
                    r="4.5" 
                    fill="#10B981" 
                    className="animate-pulse"
                  />
                </svg>

                <div className="flex justify-between items-center mt-2.5 pt-1.5 border-t border-gray-900/60 text-[10px] font-mono text-[#8E9AA7]">
                  <span>Мин: {minPrice.toFixed(2)} ₽</span>
                  <span className="text-emerald-400 font-bold shrink-0">RUB/USDT: {maxPrice.toFixed(2)} ₽</span>
                  <span>Топ: {maxPrice.toFixed(2)} ₽</span>
                </div>
              </div>

              <div className="text-[9px] text-[#8E9AA7] text-center leading-normal">
                📊 График построен по агрегированной ликвидности 12 фиатных P2P мерчантов.
              </div>
            </div>

            <div className="bg-[#161B26] border border-gray-800 p-4 rounded-3xl space-y-3">
              <span className="text-[10px] text-pink-400 uppercase font-black block">Бизнес-симулятор Операций:</span>
              <p className="text-[10px] text-[#8E9AA7]">Вы можете сбросить в исходное состояние настройки KYC или пополнить баланс.</p>
              
              <div className="grid grid-cols-2 gap-2">
                <button
                  id="btn-reset-cabinet-data"
                  onClick={resetKycSimulator}
                  className="py-2.5 rounded-xl border border-gray-800 text-gray-400 text-[10px] font-bold hover:bg-gray-800 active:scale-95 transition-all text-center"
                >
                  Сбросить KYC
                </button>
                <button
                  onClick={() => {
                    triggerHaptic.light(addHapticLog);
                    window.location.reload();
                  }}
                  className="py-2.5 rounded-xl bg-gray-800 text-white text-[10px] font-bold hover:bg-gray-750 active:scale-95 transition-all text-center flex items-center justify-center gap-1"
                >
                  <RefreshCw className="w-3 h-3" />
                  <span>Обновить API</span>
                </button>
              </div>
            </div>

          </div>
        )}

        {activeTab === "referrals" && (
          <div className="space-y-4">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Users className="w-5 h-5 text-emerald-400" />
              <span>Реферальная система</span>
            </h2>

            <div className="bg-[#161B26] border border-gray-800 p-5 rounded-3xl space-y-4 relative overflow-hidden">
              <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/3 rounded-full blur-2xl pointer-events-none" />
              
              <div className="grid grid-cols-2 gap-4 divide-x divide-gray-800">
                <div className="text-center">
                  <span className="text-[10px] text-[#8E9AA7] uppercase tracking-wider block mb-1">Рефералы</span>
                  <span className="text-2xl font-black text-white">{user?.referralsCount || 0} чел</span>
                </div>
                <div className="text-center">
                  <span className="text-[10px] text-[#8E9AA7] uppercase tracking-wider block mb-1">Всего заработано</span>
                  <span className="text-2xl font-black text-emerald-400">{user?.referralEarned.toFixed(2)} USDT</span>
                </div>
              </div>

              <div className="border-t border-gray-800/80 pt-3 flex gap-3 text-xs text-[#8E9AA7]">
                <HelpCircle className="w-4.5 h-4.5 text-amber-400 shrink-0 mt-0.5" />
                <p>Вы получаете <span className="text-white font-bold">10% от прибыли</span> сервиса с каждого завершённого обмена ваших рефералов. Начисления выплачиваются мгновенно на ваш баланс кошелька.</p>
              </div>
            </div>

            <div className="bg-[#161B26] border border-gray-800 p-4 rounded-2xl space-y-2">
              <span className="text-[10px] text-[#8E9AA7] font-semibold uppercase tracking-wider">Ваша персональная ссылка:</span>
              <div className="flex gap-2 bg-[#0B0E14] border border-gray-850 rounded-xl p-1.5 pl-3 items-center justify-between">
                <span className="text-xs text-gray-400 truncate font-mono">
                  https://t.me/usdt_telepay_bot?start=r_{user?.username}
                </span>
                <button
                  id="btn-copy-ref-link"
                  onClick={() => copyToClipboard(`https://t.me/usdt_telepay_bot?start=r_${user?.username}`, "ref_link")}
                  className="bg-[#161B26] p-2 hover:bg-[#202737] hover:text-white border border-gray-800 text-[#8E9AA7] rounded-lg relative cursor-pointer shrink-0"
                >
                  {copiedType === "ref_link" ? (
                    <Check className="w-4 h-4 text-emerald-400" />
                  ) : (
                    <Copy className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === "support" && (
          <div className="space-y-4 pb-16">
            <h2 className="text-base font-bold text-white flex items-center justify-between">
              <span className="flex items-center gap-2">
                <MessageSquare className="w-5 h-5 text-pink-400" />
                <span>Техподдержка клиентов</span>
              </span>
              <span className="text-[9px] font-mono text-[#8E9AA7] bg-[#161B26] px-1.5 py-0.5 rounded uppercase border border-white/5">
                Онлайн 24/7
              </span>
            </h2>

            {activeTicketId ? (() => {
              const activeTicket = tickets.find(t => t.id === activeTicketId);
              if (!activeTicket) return null;
              
              return (
                <div className="space-y-3.5 bg-[#0e121a]/95 border border-white/5 p-4 rounded-3xl relative overflow-hidden">
                  <div className="flex items-center justify-between pb-3 border-b border-gray-850">
                    <button 
                      onClick={() => {
                        setActiveTicketId(null);
                        triggerHaptic.light(addHapticLog);
                      }} 
                      className="text-xs font-extrabold text-[#8E9AA7] hover:text-white flex items-center gap-1 transition-colors cursor-pointer"
                    >
                      ← Назад
                    </button>
                    <div className="text-right">
                      <span className="text-[8px] uppercase tracking-wider text-gray-500 block font-bold">Номер тикета</span>
                      <span className="text-[10px] font-mono font-bold text-white bg-white/5 px-2 py-0.5 rounded-lg border border-white/5">{activeTicket.id}</span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-[11px] bg-[#121620] p-2.5 rounded-xl border border-white/5">
                    <div>
                      <span className="text-gray-400 font-medium block">Тема:</span>
                      <span className="text-white font-bold">{activeTicket.subject}</span>
                    </div>
                    <div>
                      <span className="text-gray-400 font-medium block text-right">Статус:</span>
                      {activeTicket.status === "open" ? (
                        <span className="text-[10px] text-emerald-400 font-extrabold bg-emerald-400/10 px-2 py-0.5 rounded-full uppercase tracking-wider block animate-pulse text-right">
                          Открыто
                        </span>
                      ) : (
                        <span className="text-[10px] text-gray-400 font-extrabold bg-gray-600/10 px-2 py-0.5 rounded-full uppercase tracking-wider block text-right">
                          Закрыто
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="space-y-3 max-h-72 overflow-y-auto pr-1 flex flex-col pt-1">
                    {activeTicket.messages.map((msg) => {
                      const isMe = msg.senderId === user?.id;
                      return (
                        <div 
                          key={msg.id} 
                          className={`flex flex-col max-w-[85%] ${isMe ? "self-end items-end" : "self-start items-start"}`}
                        >
                          <div className="flex items-center gap-1.5 mb-1 px-1 text-[9px]">
                            <span className={`font-extrabold ${isMe ? "text-gray-300" : "text-pink-400"}`}>
                              {isMe ? "Вы" : `${msg.senderName}`}
                            </span>
                            {!isMe && (
                              <span className="text-[7px] bg-pink-400/20 text-pink-300 px-1 rounded uppercase font-black tracking-widest scale-90">
                                {msg.senderRole === "super_admin" ? "SuperAdmin" : msg.senderRole === "admin" ? "Admin" : "Оператор"}
                              </span>
                            )}
                            <span className="text-gray-550 font-mono">
                              {new Date(msg.createdAt).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}
                            </span>
                          </div>
                          
                          <div className={`p-3 rounded-2xl relative text-xs leading-relaxed ${
                            isMe 
                              ? "bg-gradient-to-br from-[#121620] to-[#1a1e2a] text-white rounded-tr-none border border-white/5" 
                              : "bg-gradient-to-br from-[#1c121e] to-[#241328] text-white rounded-tl-none border border-pink-500/10"
                          }`}>
                            <p className="whitespace-pre-wrap">{msg.text}</p>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {activeTicket.status === "open" ? (
                    <form onSubmit={handleSendTicketMessage} className="mt-2.5 pt-2.5 border-t border-gray-850 flex items-center gap-2">
                      <input
                        type="text"
                        value={newMsgText}
                        onChange={(e) => setNewMsgText(e.target.value)}
                        placeholder="Напишите ответ..."
                        className="flex-1 bg-[#121620] text-white text-xs px-3.5 py-3 rounded-2xl border border-gray-800 focus:outline-none focus:border-pink-500 focus:ring-1 focus:ring-pink-500/20 font-sans"
                      />
                      <button 
                        type="submit"
                        disabled={!newMsgText.trim()}
                        className="w-10 h-10 flex items-center justify-center rounded-2xl bg-gradient-to-r from-pink-500 to-pink-400 text-gray-950 font-bold transition-transform active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                      >
                        <Send className="w-4 h-4" />
                      </button>
                    </form>
                  ) : (
                    <div className="text-center p-3.5 bg-gray-950/40 rounded-2xl border border-white/5 mt-1">
                      <span className="text-[10px] text-[#8E9AA7] block">Диалог закрыт. Если вопрос не решен, откройте новое обращение.</span>
                    </div>
                  )}

                  {activeTicket.status === "open" && (
                    <div className="flex justify-end pt-1">
                      <button 
                        type="button" 
                        onClick={() => {
                          triggerHaptic.light(addHapticLog);
                          handleCloseTicket(activeTicket.id);
                        }}
                        className="text-[9px] font-bold text-red-400/90 hover:text-red-300 flex items-center gap-1 transition-colors cursor-pointer"
                      >
                        🛑 Закрыть обращение как решенное
                      </button>
                    </div>
                  )}
                </div>
              );
            })() : isOpeningForm ? (
              <div className="bg-[#0e121a]/95 border border-white/5 p-4 rounded-3xl space-y-3.5">
                <div className="flex items-center justify-between pb-2 border-b border-gray-850">
                  <h3 className="text-xs font-black text-white uppercase tracking-wider flex items-center gap-1.5">
                    <Plus className="w-4 h-4 text-pink-400" />
                    Новое обращение к оператору
                  </h3>
                  <button 
                    onClick={() => {
                      setIsOpeningForm(false);
                      setSupportError("");
                      setSupportSuccess("");
                      triggerHaptic.light(addHapticLog);
                    }}
                    className="text-xs font-bold text-gray-500 hover:text-white transition-colors cursor-pointer"
                  >
                    Отмена
                  </button>
                </div>

                <form onSubmit={handleOpenTicket} className="space-y-4">
                  <div className="space-y-1.5">
                    <label className="text-[10px] text-gray-400 font-extrabold uppercase tracking-wider block">Тема обращения:</label>
                    <select
                      value={newTicketSubject}
                      onChange={(e) => {
                        triggerHaptic.light(addHapticLog);
                        setNewTicketSubject(e.target.value);
                      }}
                      className="w-full bg-[#121620] text-xs text-white p-3 rounded-2xl border border-gray-800 focus:outline-none focus:border-pink-500 font-bold"
                    >
                      <option value="Другое">Другое / Общий вопрос</option>
                      {orders.map((o) => (
                        <option key={o.id} value={`Сделка ${o.id}`}>
                          Сделка #{o.id} ({o.amountUsdt.toFixed(2)} USDT)
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-[10px] text-gray-400 font-extrabold uppercase tracking-wider block">Текст сообщения:</label>
                    <textarea
                      rows={4}
                      value={newTicketText}
                      onChange={(e) => setNewTicketText(e.target.value)}
                      placeholder="Подробно опишите вашу проблему или задайте вопрос..."
                      className="w-full bg-[#121620] text-xs text-white p-3.5 rounded-2xl border border-gray-800 focus:outline-none focus:border-pink-500 focus:ring-1 focus:ring-pink-500/20 font-sans leading-relaxed"
                    />
                  </div>

                  {supportError && (
                    <div className="text-[10px] bg-red-500/10 border border-red-500/20 text-red-400 p-2.5 rounded-xl font-bold font-mono">
                      ⚠ {supportError}
                    </div>
                  )}

                  {supportSuccess && (
                     <div className="text-[10px] bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 p-2.5 rounded-xl font-bold font-mono">
                      ✔ {supportSuccess}
                    </div>
                  )}

                  <button
                    type="submit"
                    className="w-full py-3 px-4 bg-gradient-to-r from-pink-500 to-pink-400 text-gray-950 font-black rounded-2xl transition-all uppercase text-[11px] tracking-wider flex items-center justify-center gap-1.5 cursor-pointer shadow-lg shadow-pink-500/10"
                  >
                    <Send className="w-3.5 h-3.5" />
                    <span>Отправить обращение</span>
                  </button>
                </form>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="bg-[#161B26] border border-gray-800 p-4 rounded-2xl relative overflow-hidden">
                  <div className="absolute top-0 right-0 w-16 h-16 bg-pink-500/3 rounded-full blur-xl pointer-events-none" />
                  
                  <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <Shield className="w-4 h-4 text-pink-400" />
                    Безопасность сделки СБОР
                  </h3>
                  <p className="text-[11px] text-[#8E9AA7] leading-relaxed">
                    Все сделки закупа и продажи USDT проводятся через защищённые эскроу-счета нашей P2P-платформы. 
                    Комиссия сетей TRC-20, ERC-20 и TON включена в курс обмена. Наш регламент обработки: от 5 минут до 1 часа.
                  </p>
                </div>

                <div className="bg-[#0e121a]/95 border border-white/5 rounded-3xl p-4 space-y-3.5">
                  <div className="flex items-center justify-between pb-2 border-b border-gray-850">
                    <span className="text-[10px] uppercase tracking-wider text-[#8E9AA7] font-extrabold block">Ваши обращения</span>
                    <button 
                      onClick={() => {
                        setIsOpeningForm(true);
                        setSupportError("");
                        setSupportSuccess("");
                        triggerHaptic.light(addHapticLog);
                      }}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[9px] font-black text-gray-950 bg-gradient-to-r from-pink-500 to-pink-400 rounded-xl uppercase tracking-wider cursor-pointer"
                    >
                      <Plus className="w-3.5 h-3.5 stroke-[3px]" />
                      Создать тикет
                    </button>
                  </div>

                  {ticketsLoading && tickets.length === 0 ? (
                    <div className="text-center py-6">
                      <span className="text-xs text-[#8E9AA7] animate-pulse block">Загрузка обращений...</span>
                    </div>
                  ) : tickets.length === 0 ? (
                    <div className="text-center py-7 px-4 bg-[#121620]/40 rounded-2xl border border-dashed border-gray-800">
                      <MessageCircle className="w-8 h-8 text-pink-500/30 mx-auto mb-2" />
                      <span className="text-[11px] text-gray-300 font-bold block mb-1">Нет активных обращений</span>
                      <p className="text-[10px] text-[#8E9AA7] leading-relaxed max-w-[80%] mx-auto">
                        Если у вас возник вопрос по сделке или нужна консультация, создайте обращение к оператору.
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                      {tickets.map((t) => {
                        const lastMsg = t.messages[t.messages.length - 1];
                        const dateStr = lastMsg 
                          ? new Date(lastMsg.createdAt).toLocaleDateString("ru-RU", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) 
                          : "";
                        return (
                          <div 
                            key={t.id}
                            onClick={() => {
                              setActiveTicketId(t.id);
                              triggerHaptic.light(addHapticLog);
                            }}
                            className="p-3 bg-[#121620] hover:bg-[#161B26] border border-white/5 hover:border-pink-500/10 rounded-2xl transition-all duration-150 cursor-pointer flex items-center justify-between gap-3 relative overflow-hidden group"
                          >
                            <div className="space-y-1 block flex-1">
                              <div className="flex items-center gap-2">
                                <span className="text-[10px] font-mono text-pink-400 font-extrabold bg-pink-500/5 px-1.5 py-0.2 rounded border border-pink-500/5">
                                  #{t.id}
                                </span>
                                <span className={`text-[8px] font-black uppercase px-2 py-0.2 rounded tracking-wider ${
                                  t.status === "open" ? "bg-emerald-400/10 text-emerald-400" : "bg-gray-750 text-gray-400"
                                }`}>
                                  {t.status === "open" ? "Открыт" : "Закрыт"}
                                </span>
                              </div>
                              <span className="text-xs text-white font-bold block truncate max-w-44 group-hover:text-pink-300 transition-colors">
                                {t.subject}
                              </span>
                              {lastMsg && (
                                <p className="text-[9px] text-[#8E9AA7] truncate max-w-48 italic">
                                  {lastMsg.senderId === user?.id ? "Вы: " : "Кабинет: "} {lastMsg.text}
                                </p>
                              )}
                            </div>
                            <div className="text-right flex flex-col items-end gap-1 shrink-0">
                              <span className="text-[8px] text-gray-550 font-mono block">
                                {dateStr}
                              </span>
                              <span className="text-[9px] bg-white/5 text-[#8E9AA7] px-2 py-0.5 rounded-full font-bold">
                                {t.messages.length} сообщ.
                              </span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                <div className="bg-[#161B26] border border-gray-800 p-4 rounded-2xl text-center space-y-3.5">
                  <p className="text-xs text-white">Если у вас возник экстренный вопрос, вы также можете связаться с поддержкой в мессенджере:</p>
                  
                  <a 
                    href="https://t.me/usdt_bot_support" 
                    target="_blank" 
                    rel="noreferrer"
                    onClick={() => triggerHaptic.light(addHapticLog)}
                    className="inline-flex w-full items-center justify-center gap-2 py-3 px-4 rounded-2xl bg-[#00D09E] text-gray-950 font-black text-xs uppercase tracking-wider shadow-lg shadow-[#00D09E]/10 cursor-pointer"
                  >
                    <MessageSquare className="w-4.5 h-4.5" />
                    <span>Telegram Оператор (@telepay_support)</span>
                  </a>
                </div>
              </div>
            )}
          </div>
        )}

      </div>

      <div className="fixed bottom-0 left-0 right-0 max-w-md mx-auto bg-[#0C1017]/95 backdrop-blur-xl border-t border-gray-800/60 p-2 z-40">
        <div className="grid grid-cols-5 gap-1">
          
          <button
            id="tab-btn-exchange"
            onClick={() => {
              triggerHaptic.light(addHapticLog);
              setActiveTab("exchange");
            }}
            className={`flex flex-col items-center gap-1 py-1.5 rounded-xl transition-all duration-150 cursor-pointer ${
              activeTab === "exchange" ? "text-pink-400 bg-[#161B26]/80 font-bold" : "text-[#8E9AA7] hover:text-white"
            }`}
          >
            <Wallet className="w-4.5 h-4.5" />
            <span className="text-[9px]">Обмен</span>
          </button>

          <button
            id="tab-btn-history"
            onClick={() => {
              triggerHaptic.light(addHapticLog);
              setActiveTab("history");
            }}
            className={`flex flex-col items-center gap-1 py-1.5 rounded-xl transition-all duration-150 cursor-pointer ${
              activeTab === "history" ? "text-emerald-400 bg-[#161B26]/80 font-bold" : "text-[#8E9AA7] hover:text-white"
            }`}
          >
            <Clock className="w-4.5 h-4.5" />
            <span className="text-[9px]">Сделки</span>
          </button>

          <button
            id="tab-btn-profile"
            onClick={() => {
              triggerHaptic.light(addHapticLog);
              setActiveTab("profile");
            }}
            className={`flex flex-col items-center gap-1 py-1.5 rounded-xl transition-all duration-150 relative cursor-pointer ${
              activeTab === "profile" 
                ? "text-amber-400 bg-[#161B26]/80 font-black" 
                : "text-[#8E9AA7] hover:text-white"
            }`}
          >
            {isGoldActive ? (
              <span className="absolute -top-1 right-2 w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
            ) : (
              <span className="absolute -top-1 right-2 w-2 h-2 rounded-full bg-pink-500" />
            )}
            <Award className="w-4.5 h-4.5" />
            <span className="text-[9px]">Кабинет</span>
          </button>

          <button
            id="tab-btn-referrals"
            onClick={() => {
              triggerHaptic.light(addHapticLog);
              setActiveTab("referrals");
            }}
            className={`flex flex-col items-center gap-1 py-1.5 rounded-xl transition-all duration-150 cursor-pointer ${
              activeTab === "referrals" ? "text-emerald-400 bg-[#161B26]/80 font-bold" : "text-[#8E9AA7] hover:text-white"
            }`}
          >
            <Users className="w-4.5 h-4.5" />
            <span className="text-[9px]">Рефералы</span>
          </button>

          <button
            id="tab-btn-support"
            onClick={() => {
              triggerHaptic.light(addHapticLog);
              setActiveTab("support");
            }}
            className={`flex flex-col items-center gap-1 py-1.5 rounded-xl transition-all duration-150 cursor-pointer ${
              activeTab === "support" ? "text-pink-400 bg-[#161B26]/80 font-bold" : "text-[#8E9AA7] hover:text-white"
            }`}
          >
            <MessageSquare className="w-4.5 h-4.5" />
            <span className="text-[9px]">Поддержка</span>
          </button>

        </div>
      </div>

      <AnimatePresence>
        {isKycModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-[#161B26] border border-gray-800 rounded-3xl p-6 max-w-sm w-full space-y-4 shadow-2xl relative"
            >
              <button
                onClick={() => {
                  triggerHaptic.light(addHapticLog);
                  setIsKycModalOpen(false);
                }}
                className="absolute top-4 right-4 p-1.5 rounded-full bg-[#0B0E14] text-gray-400 hover:text-white"
              >
                <X className="w-4.5 h-4.5" />
              </button>

              <div className="text-center space-y-1">
                <div className="w-12 h-12 rounded-full bg-gradient-to-tr from-amber-400 to-pink-500 flex items-center justify-center mx-auto text-xl text-gray-950 font-black shadow-lg">
                  ★
                </div>
                <h3 className="text-sm font-black text-white pt-1">Верификация до GOLD клиента</h3>
                <p className="text-[10px] text-[#8E9AA7] leading-relaxed">
                  Заполните фиатные данные ниже. Это необходимо для мгновенных зачислений на платформе без задержек оператором.
                </p>
              </div>

              {kycSuccessMessage ? (
                <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs p-4 rounded-2xl text-center space-y-2">
                  <p>{kycSuccessMessage}</p>
                  <button
                    onClick={() => {
                      triggerHaptic.light(addHapticLog);
                      setIsKycModalOpen(false);
                    }}
                    className="mt-2 w-full py-2 bg-emerald-500 text-gray-950 font-extrabold rounded-xl text-[10px]"
                  >
                    Отлично! Начать обмен
                  </button>
                </div>
              ) : (
                <form onSubmit={handleKycSubmit} className="space-y-3">
                  <div className="space-y-1">
                    <label className="text-[9px] text-[#8E9AA7] uppercase font-bold block">ФИО Держателя карт:</label>
                    <input
                      type="text"
                      placeholder="Иванов Никита Русланович"
                      required
                      value={fioInput}
                      onChange={(e) => setFioInput(e.target.value)}
                      className="w-full text-xs bg-[#0B0E14] border border-gray-800 rounded-xl p-2.5 text-white placeholder-gray-700 font-sans"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-[9px] text-[#8E9AA7] uppercase font-bold block">Номер телефона привязанный к СБП:</label>
                    <input
                      type="text"
                      placeholder="+7 999 123-4567"
                      required
                      value={phoneInput}
                      onChange={(e) => setPhoneInput(e.target.value)}
                      className="w-full text-xs bg-[#0B0E14] border border-gray-800 rounded-xl p-2.5 text-white placeholder-gray-700 font-mono"
                    />
                  </div>

                  <div className="bg-[#0B0E14] p-3 rounded-2xl text-[9px] text-[#8E9AA7] flex gap-2">
                    <Shield className="w-4.5 h-4.5 text-emerald-400 shrink-0 mt-0.5" />
                    <span>Мы гарантируем конфиденциальность. Данные используются только для сверки входящих банковских платежей P2P.</span>
                  </div>

                  <button
                    type="submit"
                    disabled={kycIsSubmitting}
                    className="w-full py-3 bg-gradient-to-r from-amber-400 via-pink-500 to-amber-500 text-gray-950 font-black rounded-xl text-xs uppercase cursor-pointer"
                  >
                    {kycIsSubmitting ? "Обработка..." : "Активировать статус GOLD"}
                  </button>
                </form>
              )}

            </motion.div>
          </div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {selectedOrder && (
          <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/75 backdrop-blur-sm">
            <div className="absolute inset-0" onClick={() => setSelectedOrder(null)} />
            
            <motion.div
              initial={{ y: "100%" }}
              animate={{ y: 0 }}
              exit={{ y: "100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 280 }}
              className="relative w-full max-w-md bg-[#161B26] border-t border-gray-800 rounded-t-[32px] p-6 space-y-4 z-10 overflow-hidden"
            >
              <div className="w-12 h-1 bg-gray-700/60 rounded-full mx-auto" />

              <div className="text-center">
                <span className="text-[10px] uppercase font-black text-pink-400 tracking-widest bg-pink-500/10 px-2.5 py-0.5 rounded-full">
                  Детали сделки #{selectedOrder.id}
                </span>
                <h3 className="text-base font-bold text-white mt-1.5">
                  {selectedOrder.orderType === "buy" ? "Покупка USDT за рубли" : "Продажа USDT за рубли"}
                </h3>
              </div>

              <div className="bg-[#0B0E14] border border-gray-850 p-4 rounded-2xl space-y-3 font-mono text-xs text-gray-300">
                <div className="flex justify-between">
                  <span className="text-[#8E9AA7]">Направление:</span>
                  <span className="text-white font-bold">{selectedOrder.orderType === "buy" ? "Покупка" : "Продажа"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#8E9AA7]">Сумма USDT:</span>
                  <span className="text-white font-bold">{selectedOrder.amountUsdt.toFixed(2)} USDT</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#8E9AA7]">Объем RUB:</span>
                  <span className="text-pink-400 font-bold">{selectedOrder.totalFiat.toFixed(2)} рублей</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#8E9AA7]">Курс обмена:</span>
                  <span className="text-white font-bold">{selectedOrder.rate.toFixed(2)} ₽/₮</span>
                </div>
                <div className="flex justify-between border-t border-gray-800/60 pt-2 text-[11px]">
                  <span className="text-[#8E9AA7]">Получатель ({selectedOrder.orderType === "buy" ? "USDT" : "RUB"}):</span>
                  <span className="text-white truncate max-w-[200px] select-all break-all" title={selectedOrder.paymentLinkSnapshot}>
                    {selectedOrder.paymentLinkSnapshot}
                  </span>
                </div>
                {selectedOrder.rejectionReason && (
                  <div className="border-t border-red-500/10 pt-2 text-red-400 text-[11px] leading-snug">
                    <span className="font-bold">Причина отклонения:</span> {selectedOrder.rejectionReason}
                  </div>
                )}
              </div>

              <div className="space-y-2 pt-2">
                {selectedOrder.status === "created" && (
                  <div className="flex gap-2.5">
                    <button
                      id="btn-complain-details"
                      onClick={() => handleFileComplaint(selectedOrder.id)}
                      disabled={selectedOrder.linkBroken}
                      className="w-1/2 py-3 px-2 rounded-xl border border-red-500/20 text-red-400 text-xs font-bold hover:bg-red-500/10 flex items-center justify-center gap-1 cursor-pointer"
                    >
                      <AlertTriangle className="w-4.5 h-4.5" />
                      <span>{selectedOrder.linkBroken ? "Жалоба подана" : "Карта не работает"}</span>
                    </button>
                    <button
                      id="btn-cancel-details"
                      onClick={() => handleCancelOrder(selectedOrder.id)}
                      className="w-1/2 py-3 px-2 rounded-xl bg-gray-850 hover:bg-gray-800 text-white text-xs font-bold flex items-center justify-center gap-1 cursor-pointer"
                    >
                      <X className="w-4.5 h-4.5" />
                      <span>Отменить сделку</span>
                    </button>
                  </div>
                )}

                <button
                  id="btn-close-details"
                  onClick={() => setSelectedOrder(null)}
                  className="w-full py-3 bg-[#161B26] hover:bg-[#202737] border border-gray-800 text-white font-bold text-xs uppercase tracking-wider rounded-xl cursor-pointer"
                >
                  Закрыть детали
                </button>
              </div>

            </motion.div>
          </div>
        )}
      </AnimatePresence>

    </div>
  );
}
