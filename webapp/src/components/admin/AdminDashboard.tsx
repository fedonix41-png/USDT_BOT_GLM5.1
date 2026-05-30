import { useState, useEffect, FormEvent } from "react";
import { useAuthStore, triggerHaptic } from "../../store/useAuthStore";
import { api } from "../../api/client";
import { ExchangeOrder, SupportTicket, UserProfile, UserRole, StatisticsData } from "../../types";
import { 
  Users, 
  Clock, 
  ShieldCheck, 
  Search, 
  Sliders, 
  X, 
  Lock, 
  Unlock, 
  AlertCircle,
  RefreshCw,
  Edit2,
  TrendingUp,
  SlidersHorizontal,
  Coins,
  MessageSquare,
  MessageCircle,
  Send
} from "lucide-react";
import { motion, AnimatePresence } from "motion/react";

export default function AdminDashboard() {
  const { user, settings, addHapticLog, refreshUserData } = useAuthStore();
  
  const [adminTab, setAdminTab] = useState<"moderation" | "crm" | "settings" | "stats" | "support">("moderation");

  const [adminTickets, setAdminTickets] = useState<SupportTicket[]>([]);
  const [adminTicketsLoading, setAdminTicketsLoading] = useState(false);
  const [activeAdminTicketId, setActiveAdminTicketId] = useState<number | null>(null);
  const [adminReplyText, setAdminReplyText] = useState("");
  
  const [searchQuery, setSearchQuery] = useState("");
  const [crmUsers, setCrmUsers] = useState<UserProfile[]>([]);
  const [editingUser, setEditingUser] = useState<UserProfile | null>(null);
  const [newBalanceVal, setNewBalanceVal] = useState("");
  const [newFiatBalanceVal, setNewFiatBalanceVal] = useState("");
  const [newUserRole, setNewUserRole] = useState<UserRole>("client");
  const [newUserStatus, setNewUserStatus] = useState<"active" | "frozen">("active");
  const [crmLoading, setCrmLoading] = useState(false);
  const [crmError, setCrmError] = useState("");
  const [crmSuccess, setCrmSuccess] = useState("");

  const [editBuyRate, setEditBuyRate] = useState("");
  const [editSellRate, setEditSellRate] = useState("");
  const [editRequisitesCard, setEditRequisitesCard] = useState("");
  const [editRequisitesWallet, setEditRequisitesWallet] = useState("");
  const [editBuyEnabled, setEditBuyEnabled] = useState(true);
  const [editSellEnabled, setEditSellEnabled] = useState(true);
  const [editBotEnabled, setEditBotEnabled] = useState(true);
  const [newChatName, setNewChatName] = useState("");
  const [tgChats, setTgChats] = useState<string[]>([]);
  
  const [settingsSuccess, setSettingsSuccess] = useState("");
  const [settingsError, setSettingsError] = useState("");

  const [adminStats, setAdminStats] = useState<StatisticsData>({
    totalOrders: 0,
    completedOrders: 0,
    cancelledOrders: 0,
    totalVolumeUsdt: 0,
    totalVolumeFiat: 0,
    buyOrders: 0,
    sellOrders: 0,
  });
  const [totalUsers, setTotalUsers] = useState(0);

  const [pendingOrders, setPendingOrders] = useState<ExchangeOrder[]>([]);
  const [selectedOrderIds, setSelectedOrderIds] = useState<number[]>([]);
  const [rejectionTargetId, setRejectionTargetId] = useState<number | null>(null);
  const [rejectionReason, setRejectionReason] = useState("");
  const [actionConfirmId, setActionConfirmId] = useState<number | null>(null);
  const [actionMsg, setActionMsg] = useState("");

  const loadModerationOrders = async () => {
    try {
      const result = await api.getAllOrders(0, 200);
      setPendingOrders(result.items.filter((o) => o.status === "created"));
    } catch (e) {
      console.error(e);
    }
  };

  const loadAdminStats = async () => {
    try {
      const [statsResult, usersResult] = await Promise.allSettled([
        api.getStatistics(),
        api.getAllUsers(0, 1),
      ]);
      if (statsResult.status === "fulfilled") {
        setAdminStats(statsResult.value);
      }
      if (usersResult.status === "fulfilled") {
        setTotalUsers(usersResult.value.total);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const loadCrmUsers = async () => {
    setCrmLoading(true);
    try {
      const result = await api.getAllUsers(0, 50, searchQuery || undefined);
      setCrmUsers(result.items);
    } catch (e) {
      console.error(e);
    } finally {
      setCrmLoading(false);
    }
  };

  useEffect(() => {
    if (settings) {
      setEditBuyRate(settings.buyRate.toString());
      setEditSellRate(settings.sellRate.toString());
      setEditRequisitesCard(settings.requisitesCard);
      setEditRequisitesWallet(settings.requisitesWallet);
      setEditBuyEnabled(settings.buyEnabled);
      setEditSellEnabled(settings.sellEnabled);
      setEditBotEnabled(settings.botEnabled);
      setTgChats(settings.notificationChats || []);
    }
  }, [settings]);

  useEffect(() => {
    loadAdminStats();
    if (adminTab === "moderation") {
      loadModerationOrders();
    }
    if (adminTab === "crm") {
      loadCrmUsers();
    }
  }, [adminTab, searchQuery]);

  const loadAdminTickets = async () => {
    try {
      const tickets = await api.getTickets();
      setAdminTickets(tickets);
    } catch (e) {
      console.error(e);
    }
  };

  const handleSendAdminReply = async (e: FormEvent) => {
    e.preventDefault();
    if (!adminReplyText.trim() || activeAdminTicketId === null) return;

    const textToSubmit = adminReplyText;
    setAdminReplyText("");

    try {
      await api.sendMessage(activeAdminTicketId, textToSubmit);
      triggerHaptic.light(addHapticLog);
      await loadAdminTickets();
    } catch (e) {
      console.error(e);
      setAdminReplyText(textToSubmit);
    }
  };

  const handleCloseAdminTicket = async (ticketId: number) => {
    try {
      await api.closeTicket(ticketId);
      triggerHaptic.success(addHapticLog);
      addHapticLog("Тикет успешно закрыт оператором", "success");
      await loadAdminTickets();
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    if (adminTab === "support") {
      setAdminTicketsLoading(true);
      loadAdminTickets().finally(() => setAdminTicketsLoading(false));

      const interval = setInterval(() => {
        loadAdminTickets();
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [adminTab]);

  const handleModerateSingle = async (orderId: number, status: "completed" | "cancelled") => {
    triggerHaptic.light(addHapticLog);
    
    if (status === "completed" && actionConfirmId !== orderId) {
      setActionConfirmId(orderId);
      addHapticLog("Модерация: Нажмите 'Подтвердить' повторно для выплаты (Double-Tap)", "light");
      setTimeout(() => setActionConfirmId(null), 3000);
      return;
    }

    try {
      await api.updateOrderStatus(
        orderId,
        status,
        status === "cancelled" ? rejectionReason : undefined
      );

      triggerHaptic.success(addHapticLog);
      setActionMsg(status === "completed" ? "Заявка успешно закрыта и выплачена!" : "Заявка отклонена, средства возвращены.");
      setRejectionTargetId(null);
      setRejectionReason("");
      setActionConfirmId(null);

      await refreshUserData();
      await loadAdminStats();
      await loadModerationOrders();
      
      setTimeout(() => setActionMsg(""), 3000);
    } catch (err: any) {
      addHapticLog(`Ошибка модерации: ${err?.message || "Unknown"}`, "error");
      triggerHaptic.error(addHapticLog);
    }
  };

  const handleToggleSelectOrder = (id: number) => {
    triggerHaptic.light(addHapticLog);
    setSelectedOrderIds(prev => 
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  const handleSelectAllPending = () => {
    triggerHaptic.light(addHapticLog);
    if (selectedOrderIds.length === pendingOrders.length) {
      setSelectedOrderIds([]);
    } else {
      setSelectedOrderIds(pendingOrders.map(p => p.id));
    }
  };

  const handleBulkModerate = async (status: "completed" | "cancelled") => {
    if (selectedOrderIds.length === 0) return;
    triggerHaptic.light(addHapticLog);

    try {
      const result = await api.bulkModerateOrders(
        selectedOrderIds,
        status,
        status === "cancelled" ? "Массовое отклонение оператором." : undefined
      );

      triggerHaptic.success(addHapticLog);
      setActionMsg(`Массово обработано: ${result.length} заявок обмена!`);
      setSelectedOrderIds([]);
      
      await refreshUserData();
      await loadAdminStats();
      await loadModerationOrders();

      setTimeout(() => setActionMsg(""), 3000);
    } catch (e) {
      console.error(e);
      triggerHaptic.error(addHapticLog);
    }
  };

  const handleSaveCrmEdit = async (e: FormEvent) => {
    e.preventDefault();
    if (!editingUser) return;
    setCrmError("");
    setCrmSuccess("");
    triggerHaptic.light(addHapticLog);

    const balanceNum = parseFloat(newBalanceVal);
    if (isNaN(balanceNum) || balanceNum < 0) {
      setCrmError("Сумма баланса должна быть положительным числом");
      triggerHaptic.error(addHapticLog);
      return;
    }

    const fiatBalanceNum = parseFloat(newFiatBalanceVal);
    if (isNaN(fiatBalanceNum) || fiatBalanceNum < 0) {
      setCrmError("Сумма фиатного баланса должна быть положительным числом");
      triggerHaptic.error(addHapticLog);
      return;
    }

    try {
      if (newUserRole !== editingUser.role) {
        await api.updateUserRole(editingUser.id, newUserRole);
      }

      if (newUserStatus === "frozen" && !editingUser.isBlocked) {
        await api.blockUser(editingUser.id);
      } else if (newUserStatus === "active" && editingUser.isBlocked) {
        await api.unblockUser(editingUser.id);
      }

      if (balanceNum !== editingUser.balance || fiatBalanceNum !== editingUser.fiatBalance) {
        await api.updateUser(editingUser.id, {
          balance: balanceNum,
          fiatBalance: fiatBalanceNum,
        });
      }

      triggerHaptic.success(addHapticLog);
      setCrmSuccess("Профиль пользователя в CRM успешно сохранен!");

      await loadCrmUsers();
      await refreshUserData();

      setTimeout(() => {
        setEditingUser(null);
        setCrmSuccess("");
      }, 1500);
    } catch (err: any) {
      setCrmError(err?.message || "Ошибка сохранения");
      triggerHaptic.error(addHapticLog);
    }
  };

  const handleSaveSettings = async (e: FormEvent) => {
    e.preventDefault();
    setSettingsError("");
    setSettingsSuccess("");
    triggerHaptic.light(addHapticLog);

    const buyNum = parseFloat(editBuyRate);
    const sellNum = parseFloat(editSellRate);

    if (isNaN(buyNum) || buyNum <= 0 || isNaN(sellNum) || sellNum <= 0) {
      setSettingsError("Разрешены только положительные курсы обмена");
      triggerHaptic.error(addHapticLog);
      return;
    }

    try {
      await api.updateExchangeSettings({
        buyRate: buyNum,
        sellRate: sellNum,
        buyEnabled: editBuyEnabled,
        sellEnabled: editSellEnabled,
        botEnabled: editBotEnabled,
        requisitesCard: editRequisitesCard.trim(),
        requisitesWallet: editRequisitesWallet.trim(),
        notificationChats: tgChats,
      });

      triggerHaptic.success(addHapticLog);
      setSettingsSuccess("Конфигурация обмена успешно сохранена!");
      await refreshUserData();
      setTimeout(() => setSettingsSuccess(""), 3000);
    } catch (err: any) {
      setSettingsError(err?.message || "Ошибка сохранения конфигурации");
      triggerHaptic.error(addHapticLog);
    }
  };

  const handleAddChat = () => {
    if (!newChatName.trim()) return;
    triggerHaptic.light(addHapticLog);
    if (!tgChats.includes(newChatName.trim())) {
      setTgChats([...tgChats, newChatName.trim()]);
    }
    setNewChatName("");
  };

  const handleRemoveChat = (nm: string) => {
    triggerHaptic.light(addHapticLog);
    setTgChats(tgChats.filter(x => x !== nm));
  };

  const isAuthorizedForSettings = user && (user.role === "admin" || user.role === "super_admin");

  const getTicketDisplayName = (ticket: SupportTicket): string => {
    const clientMsg = ticket.messages.find(m => m.senderRole === "client");
    return clientMsg?.senderName ?? `user_${ticket.userId}`;
  };

  return (
    <div className="flex-1 flex flex-col justify-between max-w-md mx-auto w-full relative pb-24">
      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        
        {/* UPPER STATUS & ROLE HEADER */}
        <div className="flex items-center justify-between border-b border-gray-800/40 pb-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-400 font-bold font-mono">
              ★
            </div>
            <div>
              <h2 className="text-sm font-extrabold text-white tracking-wide">Панель Управления</h2>
              <span className="text-[10px] text-red-400 font-bold uppercase tracking-wider block">@{user?.username} • {user?.role}</span>
            </div>
          </div>

          <button
            id="btn-admin-reload"
            onClick={async () => {
              triggerHaptic.light(addHapticLog);
              await refreshUserData();
              await loadAdminStats();
              if (adminTab === "moderation") loadModerationOrders();
              if (adminTab === "crm") loadCrmUsers();
            }}
            className="p-1.5 rounded-full bg-[#161B26] border border-gray-800 text-[#8E9AA7] hover:text-white"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {/* FEEDBACK BANNERS */}
        {actionMsg && (
          <motion.div 
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="bg-[#00D09E]/10 border border-[#00D09E]/20 text-[#00D09E] text-xs p-3.5 rounded-2xl text-center font-bold"
          >
            ✓ {actionMsg}
          </motion.div>
        )}

        {/* --- MODERATION QUEUE TAB --- */}
        {adminTab === "moderation" && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="text-xs font-bold text-[#8E9AA7] uppercase tracking-wider">Заявки обмена (Ожидают)</h3>
              
              {pendingOrders.length > 0 && (
                <button
                  id="btn-crm-select"
                  onClick={handleSelectAllPending}
                  className="text-xs text-[#00D09E] hover:underline"
                >
                  {selectedOrderIds.length === pendingOrders.length ? "Снять выбор" : "Выбрать все"}
                </button>
              )}
            </div>

            {pendingOrders.length === 0 ? (
              <div className="bg-[#161B26] border border-gray-800/40 p-12 rounded-3xl text-center space-y-2">
                <ShieldCheck className="w-10 h-10 text-[#00D09E]/55 mx-auto" />
                <h4 className="text-sm font-bold text-white">Все сделки закрыты</h4>
                <p className="text-xs text-[#8E9AA7]">Обращений обмена в очереди на обслуживание нет.</p>
              </div>
            ) : (
              <div className="space-y-3.5 max-h-[60vh] overflow-y-auto pr-0.5">
                {pendingOrders.map((ord) => {
                  const isSelected = selectedOrderIds.includes(ord.id);
                  const isConfirming = actionConfirmId === ord.id;
                  
                  return (
                    <div
                      key={ord.id}
                      className={`glass p-4 rounded-2xl space-y-3 relative transition-all duration-150 shadow-md ${
                        isSelected ? "border-[#00D09E] shadow-lg shadow-[#00D09E]/5" : "border-white/5"
                      }`}
                    >
                      {/* Highlight complaints */}
                      {ord.linkBroken && (
                        <div className="absolute top-0 bottom-0 left-0 w-1 rounded-l-2xl bg-red-500 animate-pulse" />
                      )}

                      {/* Heading specifications */}
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            id={`cb-select-order-${ord.id}`}
                            onChange={() => handleToggleSelectOrder(ord.id)}
                            className="w-4.5 h-4.5 accent-[#00D09E] cursor-pointer rounded bg-[#0b0e14] border-gray-800"
                          />
                          <span className="text-[10px] font-mono font-bold text-[#8E9AA7] uppercase">{ord.id}</span>
                        </div>
                        {ord.linkBroken && (
                          <span className="text-[9px] font-bold text-red-400 bg-red-500/10 border border-red-500/20 px-2 py-0.5 rounded-full flex items-center gap-1">
                            <AlertCircle className="w-3 h-3 text-red-500" />
                            Жалоба: Битая реквизитная карта
                          </span>
                        )}
                        <span className={`text-[10px] font-mono font-extrabold px-2 py-0.5 rounded-full ${
                          ord.orderType === "buy" ? "bg-[#00D09E]/10 text-[#00D09E]" : "bg-red-500/10 text-red-400"
                        }`}>
                          {ord.orderType === "buy" ? "Купить USDT (Рубли →)" : "Продать USDT (→ Рубли)"}
                        </span>
                      </div>

                      {/* Transaction specifications value conversion details */}
                      <div className="grid grid-cols-2 gap-2 text-xs divide-x divide-gray-850">
                        <div>
                          <span className="text-[#8E9AA7] block text-[9px] uppercase font-bold">Инициатор Telegram:</span>
                          <span className="text-white font-bold block">@{ord.username}</span>
                        </div>
                        <div className="text-right pl-2">
                          <span className="text-[#8E9AA7] block text-[9px] uppercase font-bold">Параметры операции:</span>
                          <span className="text-white font-extrabold text-sm block font-mono">
                            {ord.amountUsdt.toFixed(1)} USDT ⇄ {ord.totalFiat.toFixed(0)} ₽
                          </span>
                        </div>
                      </div>

                      {/* Target fields shown based on Buy/Sell */}
                      <div className="bg-[#0B0E14] border border-gray-850 p-2.5 rounded-xl space-y-1.5 text-[11px]">
                        <div>
                          <span className="text-[#8E9AA7] uppercase font-bold block text-[9px]">
                            {ord.orderType === "buy" ? "Кошелёк клиента получения USDT:" : "Банковские реквизиты перевода RUB:"}
                          </span>
                          <span className="font-mono text-gray-200 block break-all leading-relaxed select-all">
                            {ord.paymentLinkSnapshot}
                          </span>
                        </div>
                        <div className="border-t border-gray-800/40 pt-1">
                          <span className="text-gray-500 block text-[9px] uppercase font-bold">Реквизиты, показанные клиенту:</span>
                          <span className="text-[10px] text-gray-400 font-mono block select-all">
                            {ord.orderType === "buy" ? (settings?.requisitesCard || "—") : (settings?.requisitesWallet || "—")}
                          </span>
                        </div>
                      </div>

                      {/* Control buttons interface */}
                      <div className="flex gap-2 pt-1 border-t border-gray-850">
                        <button
                          id={`btn-reject-order-${ord.id}`}
                          onClick={() => {
                            triggerHaptic.light(addHapticLog);
                            setRejectionTargetId(ord.id);
                          }}
                          className="w-1/2 py-2.5 rounded-xl bg-red-500/15 border border-red-500/20 text-red-400 hover:bg-red-500/25 active:scale-[0.98] transition-transform text-xs font-black cursor-pointer"
                        >
                          Отклонить
                        </button>
                        
                        <button
                          id={`btn-approve-order-${ord.id}`}
                          onClick={() => handleModerateSingle(ord.id, "completed")}
                          className={`w-1/2 py-2.5 rounded-xl text-xs font-black transition-all active:scale-[0.98] cursor-pointer ${
                            isConfirming 
                              ? "bg-[#00D09E] text-[#0b0e14] animate-pulse" 
                              : "bg-[#00D09E]/10 border border-[#00D09E]/20 text-[#00D09E] hover:bg-[#00D09E]/20"
                          }`}
                        >
                          {isConfirming ? "Одобрить точно?" : "Подтвердить оплату"}
                        </button>
                      </div>

                    </div>
                  );
                })}
              </div>
            )}

            {/* Bulk actions status panel bottom shelf */}
            {selectedOrderIds.length > 0 && (
              <motion.div
                initial={{ y: 50, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                className="bg-[#161B26] border border-[#00D09E]/40 p-4.5 rounded-3xl sticky bottom-20 shadow-2xl space-y-3 z-30"
              >
                <div className="flex justify-between items-center">
                  <span className="text-xs font-bold text-white uppercase">Массовые Действия ({selectedOrderIds.length})</span>
                  <button onClick={() => setSelectedOrderIds([])} className="text-gray-500 hover:text-white">
                    <X className="w-4 h-4" />
                  </button>
                </div>
                
                <div className="grid grid-cols-2 gap-3">
                  <button
                    id="btn-bulk-reject"
                    onClick={() => handleBulkModerate("cancelled")}
                    className="py-3 bg-red-500/15 border border-red-500/30 text-red-400 text-xs font-extrabold rounded-xl hover:bg-red-500/25 cursor-pointer"
                  >
                    Отклонить все
                  </button>
                  <button
                    id="btn-bulk-approve"
                    onClick={() => handleBulkModerate("completed")}
                    className="py-3 bg-[#00D09E] hover:bg-[#00b98d] text-gray-950 text-xs font-extrabold rounded-xl shadow-lg shadow-[#00D09E]/10 cursor-pointer"
                  >
                    Подтвердить и закрыть
                  </button>
                </div>
              </motion.div>
            )}
          </div>
        )}

        {/* --- CRM TAB --- */}
        {adminTab === "crm" && (
          <div className="space-y-4">
            
            <div className="relative">
              <Search className="absolute left-3.5 top-3.5 w-4 h-4 text-gray-500" />
              <input
                type="text"
                id="crm-search-query"
                placeholder="Поиск по нику или Telegram ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full text-xs bg-[#161B26] border border-gray-800/80 focus:border-[#00D09E]/30 rounded-2xl p-4 pl-10 text-white focus:outline-none placeholder-gray-600"
              />
              {searchQuery && (
                <button 
                  onClick={() => setSearchQuery("")}
                  className="absolute right-3.5 top-3.5 text-gray-500 hover:text-white"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>

            {crmLoading ? (
              <div className="text-center py-12">
                <div className="w-6 h-6 border-2 border-[#00D09E] border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                <span className="text-xs text-[#8E9AA7]">Синхронизация CRM...</span>
              </div>
            ) : crmUsers.length === 0 ? (
              <div className="bg-[#161B26] border border-gray-800/30 p-12 rounded-3xl text-center text-xs text-[#8E9AA7]">
                Пользователи с таким ID или ником не зафиксированы.
              </div>
            ) : (
              <div className="space-y-3 max-h-[60vh] overflow-y-auto pr-0.5">
                {crmUsers.map((usr) => (
                  <div
                    key={usr.id}
                    className="bg-[#161B26] border border-gray-800/50 p-4 rounded-3xl space-y-3 relative overflow-hidden"
                  >
                    {usr.isBlocked && (
                      <div className="absolute top-0 left-0 right-0 bg-red-500/10 text-red-400 text-[10px] text-center font-bold py-1 border-b border-red-500/10">
                        ПОЛЬЗОВАТЕЛЬ ЗАБАНЕН / БЛОКИРОВКА(FROZEN)
                      </div>
                    )}
                    
                    <div className="flex justify-between items-start pt-1">
                      <div>
                        <h4 className="text-sm font-extrabold text-white">@{usr.username}</h4>
                        <span className="text-[10px] font-mono text-gray-400">Telegram ID: {usr.telegramId}</span>
                      </div>
                      <span className={`text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full ${
                        usr.role === "super_admin" 
                          ? "bg-purple-900/40 text-purple-300 border border-purple-800/40" 
                          : usr.role === "admin"
                            ? "bg-red-900/40 text-red-300 border border-red-800/40"
                            : usr.role === "operator"
                              ? "bg-blue-900/40 text-blue-300 border border-blue-800/40"
                              : "bg-gray-800 text-[#8E9AA7]"
                      }`}>
                        {usr.role === "super_admin" ? "super admin" : usr.role}
                      </span>
                    </div>

                    <div className="grid grid-cols-4 gap-1 border-t border-b border-gray-850 py-2.5 text-center">
                      <div>
                        <span className="text-[8px] text-[#8E9AA7] uppercase block font-semibold">USDT:</span>
                        <span className="text-[10px] font-bold text-emerald-400 font-mono">₮ {usr.balance.toFixed(1)}</span>
                      </div>
                      <div>
                        <span className="text-[8px] text-[#8E9AA7] uppercase block font-semibold text-pink-400">RUB:</span>
                        <span className="text-[10px] font-bold text-pink-400 font-mono">₽ {usr.fiatBalance.toFixed(0)}</span>
                      </div>
                      <div>
                        <span className="text-[8px] text-[#8E9AA7] uppercase block font-semibold text-gray-400">Рефералы:</span>
                        <span className="text-[10px] font-bold text-gray-300">{usr.referralsCount} ref</span>
                      </div>
                      <div>
                        <span className="text-[8px] text-[#8E9AA7] uppercase block font-semibold text-amber-400">Доход:</span>
                        <span className="text-[10px] font-bold text-amber-450 font-mono">₮ {usr.referralEarned.toFixed(1)}</span>
                      </div>
                    </div>

                    {/* Quick Edit Trigger */}
                    <div className="flex justify-end pt-1">
                      <button
                        id={`btn-edit-user-${usr.id}`}
                        onClick={() => {
                          triggerHaptic.light(addHapticLog);
                          setEditingUser(usr);
                          setNewBalanceVal(usr.balance.toString());
                          setNewFiatBalanceVal(usr.fiatBalance.toString());
                          setNewUserRole(usr.role);
                          setNewUserStatus(usr.isBlocked ? "frozen" : "active");
                        }}
                        className="px-3 py-1.5 rounded-xl bg-gray-800/80 hover:bg-gray-800 text-white font-semibold text-[11px] flex items-center gap-1 cursor-pointer"
                      >
                        <Edit2 className="w-3.5 h-3.5 text-[#00D09E]" />
                        <span>Управление пользователем</span>
                      </button>
                    </div>

                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* --- SYSTEM EXCHANGE CONFIGURATION SETTINGS TAB --- */}
        {adminTab === "settings" && (
          <div className="space-y-4">
            <h3 className="text-xs font-bold text-[#8E9AA7] uppercase tracking-wider">Глобальные Настройки Обменника</h3>

            {!isAuthorizedForSettings ? (
              <div className="bg-[#161B26] border border-red-500/20 p-8 rounded-3xl text-center space-y-3">
                <AlertSquareEmoji />
                <h4 className="text-sm font-bold text-white">Доступ ограничен</h4>
                <p className="text-xs text-[#8E9AA7]">
                  У вас роль <span className="text-white font-bold">{user?.role}</span>. Только Администратор (admin) или Суперадминистратор (super_admin) могут изменять курсы, реквизиты карт и выключать закуп.
                </p>
              </div>
            ) : (
              <form id="form-admin-settings" onSubmit={handleSaveSettings} className="space-y-4 text-xs">
                
                {settingsSuccess && (
                  <div className="p-3 text-center bg-[#00D09E]/10 border border-[#00D09E]/30 text-[#00D09E] font-bold rounded-2xl">
                    {settingsSuccess}
                  </div>
                )}
                {settingsError && (
                  <div className="p-3 text-center bg-red-500/10 border border-red-500/30 text-red-400 font-bold rounded-2xl">
                    {settingsError}
                  </div>
                )}

                {/* Rates config */}
                <div className="bg-[#0B0E14] border border-gray-850 p-4 rounded-2xl space-y-3">
                  <span className="text-[10px] text-[#8E9AA7] uppercase font-bold tracking-wider block">Регулировка Курсов (в рублях):</span>
                  
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <label className="text-[9px] text-[#8E9AA7] uppercase font-bold block">Курс Покупки (buy):</label>
                      <input
                        type="number"
                        step="any"
                        value={editBuyRate}
                        onChange={(e) => setEditBuyRate(e.target.value)}
                        className="w-full text-xs font-bold bg-[#161B26] border border-gray-800 focus:border-[#00D09E]/30 rounded-xl p-2.5 text-white"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[9px] text-[#8E9AA7] uppercase font-bold block">Курс Продажи (sell):</label>
                      <input
                        type="number"
                        step="any"
                        value={editSellRate}
                        onChange={(e) => setEditSellRate(e.target.value)}
                        className="w-full text-xs font-bold bg-[#161B26] border border-gray-800 focus:border-[#00D09E]/30 rounded-xl p-2.5 text-white"
                      />
                    </div>
                  </div>
                </div>

                {/* Status Toggles config */}
                <div className="bg-[#0B0E14] border border-gray-850 p-3.5 rounded-2xl space-y-2.5">
                  <span className="text-[10px] text-[#8E9AA7] uppercase font-bold tracking-wider block">Контроль функционала (Фильтры):</span>
                  
                  {/* Toggle buy */}
                  <div className="flex items-center justify-between py-1 border-b border-gray-850">
                    <div>
                      <span className="text-white font-bold block text-xs">Закуп (Покупка клиентом)</span>
                      <span className="text-[10px] text-gray-500">Вкл/выкл кнопку "Купить USDT за ₽"</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setEditBuyEnabled(!editBuyEnabled)}
                      className={`text-[10px] font-bold px-3 py-1.5 rounded-lg transition-all ${
                        editBuyEnabled ? "bg-[#00D09E]/10 text-[#00D09E] border border-[#00D09E]/20" : "bg-red-500/10 text-red-400 border border-red-500/20"
                      }`}
                    >
                      {editBuyEnabled ? "✅ Закуп вкл" : "⏸ Стоп закуп"}
                    </button>
                  </div>

                  {/* Toggle sell */}
                  <div className="flex items-center justify-between py-1 border-b border-gray-850">
                    <div>
                      <span className="text-white font-bold block text-xs">Продажа (Сдача USDT)</span>
                      <span className="text-[10px] text-gray-500">Вкл/выкл кнопку "Продать USDT за ₽"</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setEditSellEnabled(!editSellEnabled)}
                      className={`text-[10px] font-bold px-3 py-1.5 rounded-lg transition-all ${
                        editSellEnabled ? "bg-[#00D09E]/10 text-[#00D09E] border border-[#00D09E]/20" : "bg-red-500/10 text-red-400 border border-red-500/20"
                      }`}
                    >
                      {editSellEnabled ? "✅ Продажа вкл" : "⏸ Стоп продажа"}
                    </button>
                  </div>

                  {/* Toggle bot enabled */}
                  <div className="flex items-center justify-between py-1">
                    <div>
                      <span className="text-white font-bold block text-xs">Глобальная работа бота</span>
                      <span className="text-[10px] text-gray-505 text-red-400 font-bold">Полное выключение для клиентов</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setEditBotEnabled(!editBotEnabled)}
                      className={`text-[10px] font-bold px-3 py-1.5 rounded-lg transition-all ${
                        editBotEnabled ? "bg-[#00D09E]/10 text-[#00D09E] border border-[#00D09E]/20" : "bg-red-500/20 text-red-400 border border-red-500/40"
                      }`}
                    >
                      {editBotEnabled ? "✅ Включен" : "🛑 ОТКЛЮЧИТЬ"}
                    </button>
                  </div>
                </div>

                {/* Requisites Details */}
                <div className="bg-[#0B0E14] border border-gray-850 p-4 rounded-2xl space-y-3">
                  <span className="text-[10px] text-[#8E9AA7] uppercase font-bold tracking-wider block">Управление Реквизитами Получения:</span>
                  
                  <div className="space-y-2">
                    <div className="space-y-1">
                      <label className="text-[9px] text-[#8E9AA7] uppercase font-bold block">Реквизиты RUB (Карта для Buy):</label>
                      <input
                        type="text"
                        value={editRequisitesCard}
                        onChange={(e) => setEditRequisitesCard(e.target.value)}
                        placeholder="Банковская карта для рублей..."
                        className="w-full text-xs font-semibold bg-[#161B26] border border-gray-850 focus:border-[#00D09E]/30 rounded-xl p-2.5 text-white"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[9px] text-[#8E9AA7] uppercase font-bold block">Реквизиты USDT (Wallet для Sell):</label>
                      <input
                        type="text"
                        value={editRequisitesWallet}
                        onChange={(e) => setEditRequisitesWallet(e.target.value)}
                        placeholder="USDT Адрес TRC-20..."
                        className="w-full text-xs font-semibold bg-[#161B26] border border-gray-850 focus:border-[#00D09E]/30 rounded-xl p-2.5 text-white"
                      />
                    </div>
                  </div>
                </div>

                {/* Audit notification Group chats */}
                <div className="bg-[#0B0E14] border border-gray-850 p-4 rounded-2xl space-y-3">
                  <span className="text-[10px] text-[#8E9AA7] uppercase font-bold block">Телеграм чаты уведомлений:</span>
                  
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="Например @alerts_telepay..."
                      value={newChatName}
                      onChange={(e) => setNewChatName(e.target.value)}
                      className="flex-1 text-xs bg-[#161B26] border border-gray-850 rounded-xl p-2 focus:outline-none"
                    />
                    <button
                      type="button"
                      id="btn-add-chat-notif"
                      onClick={handleAddChat}
                      className="px-3 bg-[#00D09E] text-gray-950 font-bold rounded-xl"
                    >
                      ➕
                    </button>
                  </div>

                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {tgChats.length === 0 ? (
                      <span className="text-gray-650 text-[10px]">Список пуст...</span>
                    ) : (
                      tgChats.map(c => (
                        <span key={c} className="bg-gray-800/80 border border-gray-700 font-bold font-mono text-[10px] text-[#8E9AA7] px-2 py-1 rounded-lg flex items-center gap-1">
                          <span>{c}</span>
                          <button type="button" onClick={() => handleRemoveChat(c)} className="hover:text-red-400">
                            ×
                          </button>
                        </span>
                      ))
                    )}
                  </div>
                </div>

                {/* Save button */}
                <button
                  type="submit"
                  id="btn-save-exchange-config"
                  className="w-full py-4 bg-[#00D09E] hover:bg-[#00b98d] text-gray-950 font-bold uppercase rounded-2xl cursor-pointer shadow-lg shadow-[#00D09E]/5"
                >
                  Сохранить настройки
                </button>

              </form>
            )}
          </div>
        )}

        {/* --- DETAILED STATS TAB --- */}
        {adminTab === "stats" && (
          <div className="space-y-4">
            <h3 className="text-xs font-bold text-[#8E9AA7] uppercase tracking-wider">Статистика систем обменника</h3>
            
            <div className="grid grid-cols-1 gap-3.5">
              <div className="bg-[#161B26] border border-gray-800/40 p-5 rounded-3xl flex justify-between items-center relative overflow-hidden">
                <div className="absolute top-0 right-0 w-24 h-24 bg-pink-500/1 rounded-full blur-2xl" />
                <div>
                  <span className="text-[10px] text-[#8E9AA7] uppercase font-bold tracking-wider block">Зарегано участников бота</span>
                  <p className="text-3xl font-black text-white mt-1 font-mono">{totalUsers} чел</p>
                </div>
                <Users className="w-10 h-10 text-pink-500/40" />
              </div>

              <div className="bg-[#161B26] border border-gray-800/40 p-5 rounded-3xl flex justify-between items-center relative overflow-hidden">
                <div className="absolute top-0 right-0 w-24 h-24 bg-[#00D09E]/1 rounded-full blur-2xl" />
                <div>
                  <span className="text-[10px] text-[#8E9AA7] uppercase font-bold tracking-wider block">Оборот RUB (Закрытые сделки)</span>
                  <p className="text-3xl font-black text-[#00D09E] mt-1 font-mono">₽ {adminStats.totalVolumeFiat.toLocaleString("ru-RU", { maximumFractionDigits: 0 })}</p>
                </div>
                <TrendingUp className="w-10 h-10 text-[#00D09E]/30" />
              </div>

              <div className="bg-[#161B26] border border-gray-800/40 p-5 rounded-3xl flex justify-between items-center relative overflow-hidden">
                <div>
                  <span className="text-[10px] text-[#8E9AA7] uppercase font-bold tracking-wider block">Оборот USDT (Закрытые сделки)</span>
                  <p className="text-3xl font-black text-white mt-1 font-mono">₮ {adminStats.totalVolumeUsdt.toLocaleString("ru-RU", { maximumFractionDigits: 1 })} USDT</p>
                </div>
                <Coins className="w-10 h-10 text-[#00D09E]/20" />
              </div>

              <div className="bg-[#161B26] border border-gray-800/40 p-4 rounded-3xl space-y-2">
                <span className="text-[10px] text-[#8E9AA7] uppercase font-bold tracking-wider block">Постоянные лимиты:</span>
                <div className="space-y-1.5 text-xs">
                  <div className="flex justify-between text-[#8E9AA7]">
                    <span>Минимальная сумма обмена:</span>
                    <span className="text-white font-bold font-mono">10 USDT</span>
                  </div>
                  <div className="flex justify-between text-[#8E9AA7]">
                    <span>Лимит разового закупа (RUB):</span>
                    <span className="text-white font-bold font-mono">500,000 Рублей</span>
                  </div>
                  <div className="flex justify-between text-[#8E9AA7]">
                    <span>Регламент ручной модерации:</span>
                    <span className="text-[#00D09E] font-bold">1 час (макс)</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* --- OPERATOR SUPPORT TICKETS TAB --- */}
        {adminTab === "support" && (
          <div className="space-y-4 pb-16">
            <h3 className="text-sm font-bold text-white flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <MessageSquare className="w-5 h-5 text-[#00D09E]" />
                <span>Тикеты техподдержки CRM</span>
              </span>
              <span className="text-[9px] bg-[#00D09E]/10 text-[#00D09E] px-2 py-0.5 rounded font-black font-mono">
                {adminTickets.filter(t => t.status === "open").length} OPEN
              </span>
            </h3>

            {activeAdminTicketId !== null ? (() => {
              const ticket = adminTickets.find(t => t.id === activeAdminTicketId);
              if (!ticket) return null;

              return (
                <div className="space-y-3.5 bg-[#161B26] border border-gray-800/40 p-4 rounded-3xl relative">
                  <div className="flex items-center justify-between pb-2.5 border-b border-gray-800">
                    <button 
                      onClick={() => {
                        setActiveAdminTicketId(null);
                        triggerHaptic.light(addHapticLog);
                      }}
                      className="text-xs font-bold text-[#8E9AA7] hover:text-white flex items-center gap-1 cursor-pointer"
                    >
                      ← К списку тикетов
                    </button>
                    <span className="text-[10px] font-mono font-bold text-white bg-white/5 px-2 py-0.5 rounded">{ticket.id}</span>
                  </div>

                  {/* Summary info */}
                  <div className="bg-[#121620] p-3 rounded-2xl border border-white/5 text-xs space-y-1">
                    <div className="flex justify-between">
                      <span className="text-gray-400">Пользователь:</span>
                      <span className="text-white font-bold font-mono">@{getTicketDisplayName(ticket)} (ID: {ticket.userId})</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Тема:</span>
                      <span className="text-[#00D09E] font-bold">{ticket.subject}</span>
                    </div>
                    <div className="flex justify-between items-center pt-1 border-t border-gray-800 mt-1">
                      <span className="text-gray-400">Статус:</span>
                      {ticket.status === "open" ? (
                        <span className="text-[9px] text-emerald-400 font-extrabold bg-emerald-400/10 px-1.5 py-0.2 rounded uppercase animate-pulse">
                          Открыт
                        </span>
                      ) : (
                        <span className="text-[9px] text-gray-400 font-extrabold bg-gray-600/15 px-1.5 py-0.2 rounded uppercase">
                          Закрыт
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Messages feed */}
                  <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1 flex flex-col pt-1">
                    {ticket.messages.map((msg) => {
                      const isOperator = msg.senderRole !== "client";
                      return (
                        <div 
                          key={msg.id} 
                          className={`flex flex-col max-w-[85%] ${isOperator ? "self-end items-end" : "self-start items-start"}`}
                        >
                          <div className="flex items-center gap-1 px-1.5 text-[9px] mb-0.5">
                            <span className={`font-bold ${isOperator ? "text-[#00D09E]" : "text-pink-400"}`}>
                              {isOperator ? `${msg.senderName} (Поддержка)` : `@${msg.senderName}`}
                            </span>
                            <span className="text-gray-550 font-mono">
                              {new Date(msg.createdAt).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}
                            </span>
                          </div>
                          
                          <div className={`p-3 rounded-2xl text-xs leading-relaxed ${
                            isOperator 
                              ? "bg-gradient-to-br from-[#121620] to-[#1a1e2a] text-white rounded-tr-none border border-white/5" 
                              : "bg-gradient-to-br from-[#1c121e] to-[#241328] text-white rounded-tl-none border border-pink-500/10"
                          }`}>
                            <p className="whitespace-pre-wrap">{msg.text}</p>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Reply container */}
                  {ticket.status === "open" ? (
                    <form onSubmit={handleSendAdminReply} className="mt-3 pt-3 border-t border-gray-800 flex items-center gap-2">
                      <input
                        type="text"
                        value={adminReplyText}
                        onChange={(e) => setAdminReplyText(e.target.value)}
                        placeholder="Наберите ответ клиенту..."
                        className="flex-1 bg-[#121620] text-white text-xs px-3.5 py-3 rounded-2xl border border-gray-800 focus:outline-none focus:border-[#00D09E] font-sans"
                      />
                      <button 
                        type="submit"
                        disabled={!adminReplyText.trim()}
                        className="w-10 h-10 flex items-center justify-center rounded-2xl bg-gradient-to-r from-[#00D09E] to-[#10B981] text-gray-950 font-bold transition-transform active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                      >
                        <Send className="w-4 h-4" />
                      </button>
                    </form>
                  ) : (
                    <div className="text-center p-3.5 bg-gray-950/40 rounded-2xl border border-white/5 mt-1">
                      <span className="text-[10px] text-gray-400 block font-bold">Обращение закрыто оператором.</span>
                    </div>
                  )}

                  {/* Complete actions */}
                  {ticket.status === "open" && (
                    <div className="flex justify-end pt-1">
                      <button 
                        type="button" 
                        onClick={() => {
                          triggerHaptic.light(addHapticLog);
                          handleCloseAdminTicket(ticket.id);
                        }}
                        className="text-[9px] font-bold text-red-400/90 hover:text-red-300 flex items-center gap-1 transition-colors cursor-pointer"
                      >
                        🛑 Закрыть тикет как решенный
                      </button>
                    </div>
                  )}
                </div>
              );
            })() : (
              // Display tickets items list
              <div className="bg-[#161B26] border border-gray-800/40 rounded-3xl p-4.5 space-y-3.5">
                <span className="text-[10px] uppercase font-bold tracking-wider text-[#8E9AA7] block">Список обращений клиентов</span>
                
                {adminTicketsLoading && adminTickets.length === 0 ? (
                  <div className="text-center py-6">
                    <span className="text-xs text-[#8E9AA7] animate-pulse block">Загрузка тикетов техподдержки...</span>
                  </div>
                ) : adminTickets.length === 0 ? (
                  <div className="text-center py-7 px-4 bg-[#121620]/30 rounded-2xl border border-dashed border-gray-800">
                    <MessageCircle className="w-8 h-8 text-[#00D09E]/30 mx-auto mb-2" />
                    <span className="text-[11px] text-gray-300 font-bold block mb-1">Нет активных тикетов</span>
                    <p className="text-[10px] text-[#8E9AA7] leading-relaxed max-w-[80%] mx-auto">
                      Клиенты еще не отправляли обращений в поддержку.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                    {adminTickets.map((t) => {
                      const lastMsg = t.messages[t.messages.length - 1];
                      const dateStr = lastMsg 
                        ? new Date(lastMsg.createdAt).toLocaleDateString("ru-RU", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) 
                        : "";
                      return (
                        <div 
                          key={t.id}
                          onClick={() => {
                            setActiveAdminTicketId(t.id);
                            triggerHaptic.light(addHapticLog);
                          }}
                          className={`p-3 bg-[#121620] hover:bg-gray-850/30 border rounded-2xl transition-all duration-150 cursor-pointer flex items-center justify-between gap-3 relative ${
                            t.status === "open" ? "border-[#00D09E]/20" : "border-white/5 opacity-70"
                          }`}
                        >
                          <div className="space-y-1 block flex-1 truncate">
                            <div className="flex items-center gap-1.5 flex-wrap">
                              <span className="text-[10px] font-mono text-white bg-white/5 px-1.5 py-0.2 rounded">
                                {t.id}
                              </span>
                              <span className="text-[10px] font-mono font-bold text-[#00D09E]">
                                @{getTicketDisplayName(t)}
                              </span>
                              <span className={`text-[8px] font-black uppercase px-2 py-0.2 rounded tracking-wider ${
                                t.status === "open" ? "bg-emerald-400/10 text-emerald-400 animate-pulse" : "bg-gray-750 text-gray-400"
                              }`}>
                                {t.status === "open" ? "Open" : "Closed"}
                              </span>
                            </div>
                            <span className="text-xs text-white font-bold block truncate">
                              Тема: {t.subject}
                            </span>
                            {lastMsg && (
                              <p className="text-[9px] text-[#8E9AA7] truncate italic">
                                {lastMsg.senderRole !== "client" ? "Вы: " : "Кабинет: "} {lastMsg.text}
                              </p>
                            )}
                          </div>
                          <div className="text-right flex flex-col items-end gap-1 shrink-0">
                            <span className="text-[8px] text-gray-550 font-mono block">
                              {dateStr}
                            </span>
                            <span className="text-[9px] bg-[#00D09E]/5 text-[#00D09E] px-2 py-0.5 rounded-full font-bold">
                              {t.messages.length} сообщ.
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

      </div>

      {/* FOOTER TAB BAR (Admin / Operator scope) */}
      <div className="fixed bottom-0 left-0 right-0 max-w-md mx-auto bg-[#0f131c]/95 backdrop-blur-xl border-t border-gray-800/70 p-2.5 z-40">
        <div className="grid grid-cols-5 gap-1">
          <button
            id="tab-admin-moderation"
            onClick={() => {
              triggerHaptic.light(addHapticLog);
              setAdminTab("moderation");
            }}
            className={`flex flex-col items-center gap-1.5 py-2.5 rounded-xl transition-all duration-150 cursor-pointer ${
              adminTab === "moderation" ? "text-[#00D09E] bg-[#161B26]/80 font-bold" : "text-[#8E9AA7] hover:text-white"
            }`}
          >
            <Clock className="w-5 h-5" />
            <span className="text-[10px]">Заявки ({pendingOrders.length})</span>
          </button>

          <button
            id="tab-admin-crm"
            onClick={() => {
              triggerHaptic.light(addHapticLog);
              setAdminTab("crm");
            }}
            className={`flex flex-col items-center gap-1.5 py-2.5 rounded-xl transition-all duration-150 cursor-pointer ${
              adminTab === "crm" ? "text-[#00D09E] bg-[#161B26]/80 font-bold" : "text-[#8E9AA7] hover:text-white"
            }`}
          >
            <Users className="w-5 h-5" />
            <span className="text-[10px]">Пользователи</span>
          </button>

          <button
            id="tab-admin-support"
            onClick={() => {
              triggerHaptic.light(addHapticLog);
              setAdminTab("support");
            }}
            className={`flex flex-col items-center gap-1.5 py-2.5 rounded-xl transition-all duration-150 cursor-pointer relative ${
              adminTab === "support" ? "text-[#00D09E] bg-[#161B26]/80 font-bold" : "text-[#8E9AA7] hover:text-white"
            }`}
          >
            <MessageSquare className="w-5 h-5" />
            <span className="text-[10px]">Поддержка</span>
            {adminTickets.filter(t => t.status === "open").length > 0 && (
              <span className="absolute top-1.5 right-4 bg-red-500 text-[8px] text-white font-black px-1.5 py-0.5 rounded-full uppercase tracking-wider animate-pulse font-mono">
                {adminTickets.filter(t => t.status === "open").length}
              </span>
            )}
          </button>

          <button
            id="tab-admin-settings"
            onClick={() => {
              triggerHaptic.light(addHapticLog);
              setAdminTab("settings");
            }}
            className={`flex flex-col items-center gap-1.5 py-2.5 rounded-xl transition-all duration-150 cursor-pointer ${
              adminTab === "settings" ? "text-[#00D09E] bg-[#161B26]/80 font-bold" : "text-[#8E9AA7] hover:text-white"
            }`}
          >
            <Sliders className="w-5 h-5" />
            <span className="text-[10px]">Управление</span>
          </button>

          <button
            id="tab-admin-stats"
            onClick={() => {
              triggerHaptic.light(addHapticLog);
              setAdminTab("stats");
            }}
            className={`flex flex-col items-center gap-1.5 py-2.5 rounded-xl transition-all duration-150 cursor-pointer ${
              adminTab === "stats" ? "text-[#00D09E] bg-[#161B26]/80 font-bold" : "text-[#8E9AA7] hover:text-white"
            }`}
          >
            <SlidersHorizontal className="w-5 h-5" />
            <span className="text-[10px]">Инфо</span>
          </button>
        </div>
      </div>

      {/* --- REJECTION DIALOG DRAWER --- */}
      <AnimatePresence>
        {rejectionTargetId !== null && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-[#161B26] border border-gray-800 rounded-3xl p-5 w-full max-w-sm space-y-4"
            >
              <div>
                <h4 className="text-sm font-bold text-white uppercase tracking-wider text-center flex items-center justify-center gap-1.5">
                  <AlertCircle className="w-4.5 h-4.5 text-red-500" />
                  <span>Отклонение заявки</span>
                </h4>
                <p className="text-xs text-[#8E9AA7] text-center mt-1">Укажите причину для информирования пользователя</p>
              </div>

              <div className="space-y-1.5">
                <label className="text-[10px] text-[#8E9AA7] uppercase font-bold">Причина отклонения:</label>
                <textarea
                  id="textarea-rejection-reason"
                  placeholder="Пример: Деньги на карту не поступили, неверная сумма перевода..."
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  className="w-full text-xs bg-[#0b0e14] border border-gray-805 text-white placeholder-gray-650 rounded-xl p-3 h-24 focus:outline-none focus:border-red-500/50 resize-none"
                />
              </div>

              <div className="flex gap-2">
                <button
                  id="btn-close-rejection-prompt"
                  onClick={() => {
                    triggerHaptic.light(addHapticLog);
                    setRejectionTargetId(null);
                    setRejectionReason("");
                  }}
                  className="w-1/2 py-2.5 bg-[#0b0e14] border border-gray-800 text-white text-xs font-bold rounded-xl cursor-pointer"
                >
                  Отмена
                </button>
                <button
                  id="btn-confirm-rejection"
                  onClick={() => handleModerateSingle(rejectionTargetId!, "cancelled")}
                  className="w-1/2 py-2.5 bg-red-500 hover:bg-red-650 text-white text-xs font-bold rounded-xl cursor-pointer"
                >
                  Отклонить заявку
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* --- CRM ACCOUNT EDIT DIALOG MODAL --- */}
      <AnimatePresence>
        {editingUser && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-[#161B26] border border-gray-800 rounded-3xl p-5 w-full max-w-sm space-y-4"
            >
              <div className="flex justify-between items-center border-b border-gray-800 pb-2.5">
                <div>
                  <h4 className="text-sm font-extrabold text-white">Режим CRM: @{editingUser.username}</h4>
                  <span className="text-[10px] text-gray-500 font-mono">Telegram ID: {editingUser.telegramId}</span>
                </div>
                <button 
                  onClick={() => {
                    triggerHaptic.light(addHapticLog);
                    setEditingUser(null);
                  }} 
                  className="text-gray-500 hover:text-white"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {crmError && (
                <div className="text-xs text-red-500 bg-red-500/10 border border-red-500/20 p-2 rounded-xl text-center font-bold">
                  ⚠️ {crmError}
                </div>
              )}
              {crmSuccess && (
                <div className="text-xs text-[#00D09E] bg-[#00D09E]/10 border border-[#00D09E]/20 p-2 rounded-xl text-center font-bold">
                  {crmSuccess}
                </div>
              )}

              <form id="form-crm-user-edit" onSubmit={handleSaveCrmEdit} className="space-y-4 text-xs">
                
                {/* Adjust User Balance */}
                <div className="space-y-1.5">
                  <label className="text-[10px] text-[#8E9AA7] font-bold uppercase tracking-wider block">Изменить баланс кошелька (USDT):</label>
                  <input
                    type="number"
                    step="any"
                    value={newBalanceVal}
                    onChange={(e) => setNewBalanceVal(e.target.value)}
                    className="w-full text-xs font-bold bg-[#0b0e14] border border-gray-800 text-white p-3 rounded-xl focus:outline-none focus:border-[#00D09E]"
                  />
                </div>

                {/* Adjust User Fiat Balance */}
                <div className="space-y-1.5">
                  <label className="text-[10px] text-pink-400 font-bold uppercase tracking-wider block">Изменить фиатный баланс (RUB):</label>
                  <input
                    type="number"
                    step="any"
                    value={newFiatBalanceVal}
                    onChange={(e) => setNewFiatBalanceVal(e.target.value)}
                    className="w-full text-xs font-bold bg-[#0b0e14] border border-gray-800 text-white p-3 rounded-xl focus:outline-none focus:border-[#00D09E]"
                  />
                </div>

                {/* Adjust Role */}
                <div className="space-y-1.5">
                  <span className="text-[10px] text-[#8E9AA7] font-bold uppercase tracking-wider block">Назначить роль RBAC:</span>
                  <div className="grid grid-cols-2 gap-1 bg-[#0b0e14] p-1 rounded-xl">
                    {(["client", "operator", "admin", "super_admin"] as const).map((r) => (
                      <button
                        key={r}
                        type="button"
                        id={`crm-set-role-${r}`}
                        onClick={() => {
                          triggerHaptic.light(addHapticLog);
                          setNewUserRole(r);
                        }}
                        className={`py-1.5 rounded-lg text-[10px] font-bold transition-all ${
                          newUserRole === r 
                            ? "bg-[#161B26] border border-gray-800 text-[#00D09E]" 
                            : "text-gray-500 hover:text-white"
                        }`}
                      >
                        {r === "super_admin" ? "super admin" : r}
                      </button>
                    ))}
                  </div>
                  <span className="text-[9px] text-gray-500 leading-snug block">
                    * Помните: admin может повышать только до уровня operator. Только super_admin имеет привилегию наделять других ролью admin.
                  </span>
                </div>

                {/* Adjust Status */}
                <div className="space-y-1.5">
                  <label className="text-[10px] text-[#8E9AA7] font-bold uppercase tracking-wider block">Статус пользователя в боте:</label>
                  <div className="grid grid-cols-2 gap-1.5">
                    <button
                      type="button"
                      id="crm-status-active"
                      onClick={() => {
                        triggerHaptic.light(addHapticLog);
                        setNewUserStatus("active");
                      }}
                      className={`py-2 px-1 rounded-lg text-[10px] font-bold border transition-all flex items-center justify-center gap-1 cursor-pointer ${
                        newUserStatus === "active" 
                          ? "bg-[#00D09E]/10 border-[#00D09E]/30 text-[#00D09E]" 
                          : "bg-[#0b0e14] border-gray-850 text-gray-500 hover:text-white font-semibold"
                      }`}
                    >
                      <Unlock className="w-3.5 h-3.5" />
                      <span>Активен</span>
                    </button>
                    <button
                      type="button"
                      id="crm-status-frozen"
                      onClick={() => {
                        triggerHaptic.light(addHapticLog);
                        setNewUserStatus("frozen");
                      }}
                      className={`py-2 px-1 rounded-lg text-[10px] font-bold border transition-all flex items-center justify-center gap-1 cursor-pointer ${
                        newUserStatus === "frozen" 
                          ? "bg-red-500/10 border-red-500/30 text-red-400" 
                          : "bg-[#0b0e14] border-gray-850 text-gray-500 hover:text-white font-semibold"
                      }`}
                    >
                      <Lock className="w-3.5 h-3.5" />
                      <span>Забанить</span>
                    </button>
                  </div>
                </div>

                <div className="flex gap-2 pt-2 border-t border-gray-800/60">
                  <button
                    type="button"
                    onClick={() => {
                      triggerHaptic.light(addHapticLog);
                      setEditingUser(null);
                    }}
                    className="w-1/2 py-2.5 bg-gray-800 hover:bg-gray-750 text-white font-extrabold rounded-xl cursor-pointer"
                  >
                    Отмена
                  </button>
                  <button
                    type="submit"
                    className="w-1/2 py-2.5 bg-[#00D09E] hover:bg-[#00b98d] text-gray-950 font-extrabold rounded-xl cursor-pointer shadow-lg shadow-[#00D09E]/5"
                  >
                    Сохранить
                  </button>
                </div>
              </form>

            </motion.div>
          </div>
        )}
      </AnimatePresence>

    </div>
  );
}

function AlertSquareEmoji() {
  return (
    <div className="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center mx-auto text-xl text-red-500">
      ⚠️
    </div>
  );
}
