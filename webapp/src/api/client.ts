import { useAuthStore } from "../store/useAuthStore";
import {
  mapUserResponse,
  mapOrderResponse,
  mapSettingsResponse,
  mapTicketResponse,
  mapMessageResponse,
  mapStatisticsResponse,
  toOrderCreatePayload,
} from "./mappers";
import type {
  UserProfile,
  ExchangeOrder,
  SystemSettings,
  SupportTicket,
  SupportMessage,
  StatisticsData,
  OrderCreateRequest,
  UserRole,
  OrderStatus,
} from "../types";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = useAuthStore.getState().token;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(path, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    useAuthStore.getState().logout();
    throw new ApiError(401, "Unauthorized");
  }

  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      message = body.detail ?? body.message ?? message;
    } catch {
      /* ignore parse failure */
    }
    throw new ApiError(response.status, message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export const api = {
  /* ── Auth ─────────────────────────────────────────── */

  verifyTelegram(initData: string): Promise<{ token: string; user: UserProfile }> {
    return request("/api/v1/auth/telegram/verify", {
      method: "POST",
      body: JSON.stringify({ initData }),
    }).then((raw) => ({
      token: (raw as Record<string, unknown>).token as string,
      user: mapUserResponse((raw as Record<string, unknown>).user as Record<string, unknown>),
    }));
  },

  /* ── User ─────────────────────────────────────────── */

  getProfile(): Promise<UserProfile> {
    return request("/api/v1/user/profile").then((raw) =>
      mapUserResponse(raw as Record<string, unknown>)
    );
  },

  getUserOrders(offset = 0, limit = 20): Promise<{ items: ExchangeOrder[]; total: number }> {
    return request(`/api/v1/user/orders?offset=${offset}&limit=${limit}`).then((raw) => {
      const d = raw as Record<string, unknown>;
      const items = Array.isArray(d.items)
        ? (d.items as Record<string, unknown>[]).map(mapOrderResponse)
        : [];
      return { items, total: (d.total as number) ?? items.length };
    });
  },

  /* ── Orders ──────────────────────────────────────── */

  createOrder(orderType: string, amountUsdt: number, clientDetails: string): Promise<ExchangeOrder> {
    const payload = toOrderCreatePayload({ orderType: orderType as OrderCreateRequest["orderType"], amountUsdt, clientDetails });
    return request("/api/v1/orders", {
      method: "POST",
      body: JSON.stringify(payload),
    }).then((raw) => mapOrderResponse(raw as Record<string, unknown>));
  },

  cancelOrder(orderId: number): Promise<ExchangeOrder> {
    return request(`/api/v1/orders/${orderId}/cancel`, { method: "POST" }).then((raw) =>
      mapOrderResponse(raw as Record<string, unknown>)
    );
  },

  complainOrder(orderId: number): Promise<ExchangeOrder> {
    return request(`/api/v1/orders/${orderId}/complain`, { method: "POST" }).then((raw) =>
      mapOrderResponse(raw as Record<string, unknown>)
    );
  },

  /* ── Settings ────────────────────────────────────── */

  getExchangeSettings(): Promise<SystemSettings> {
    return request("/api/v1/exchange/settings").then((raw) =>
      mapSettingsResponse(raw as Record<string, unknown>)
    );
  },

  updateExchangeSettings(data: Partial<SystemSettings>): Promise<SystemSettings> {
    const payload: Record<string, unknown> = {};
    if (data.buyRate !== undefined) payload.buy_rate = data.buyRate;
    if (data.sellRate !== undefined) payload.sell_rate = data.sellRate;
    if (data.buyEnabled !== undefined) payload.buy_enabled = data.buyEnabled;
    if (data.sellEnabled !== undefined) payload.sell_enabled = data.sellEnabled;
    if (data.botEnabled !== undefined) payload.bot_enabled = data.botEnabled;
    if (data.requisitesCard !== undefined) payload.requisites_card = data.requisitesCard;
    if (data.requisitesWallet !== undefined) payload.requisites_wallet = data.requisitesWallet;
    if (data.notificationChats !== undefined) payload.notification_chats = data.notificationChats;

    return request("/api/v1/exchange/settings", {
      method: "PUT",
      body: JSON.stringify(payload),
    }).then((raw) => mapSettingsResponse(raw as Record<string, unknown>));
  },

  /* ── Rates ────────────────────────────────────────── */

  getRatesHistory(type?: string, limit = 50): Promise<unknown[]> {
    const params = new URLSearchParams();
    if (type) params.set("type", type);
    params.set("limit", String(limit));
    return request(`/api/v1/rates/history?${params}`).then((raw) => raw as unknown[]);
  },

  /* ── Admin: Users ────────────────────────────────── */

  getAllUsers(offset = 0, limit = 20, search?: string): Promise<{ items: UserProfile[]; total: number }> {
    const params = new URLSearchParams({ offset: String(offset), limit: String(limit) });
    if (search) params.set("search", search);
    return request(`/api/v1/admin/users?${params}`).then((raw) => {
      const d = raw as Record<string, unknown>;
      const items = Array.isArray(d.items)
        ? (d.items as Record<string, unknown>[]).map(mapUserResponse)
        : [];
      return { items, total: (d.total as number) ?? items.length };
    });
  },

  updateUser(userId: number, data: Partial<UserProfile>): Promise<UserProfile> {
    const payload: Record<string, unknown> = {};
    if (data.username !== undefined) payload.username = data.username;
    if (data.fullName !== undefined) payload.full_name = data.fullName;
    if (data.role !== undefined) payload.role = data.role;
    return request(`/api/v1/admin/users/${userId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }).then((raw) => mapUserResponse(raw as Record<string, unknown>));
  },

  blockUser(userId: number): Promise<UserProfile> {
    return request(`/api/v1/admin/users/${userId}/block`, { method: "POST" }).then((raw) =>
      mapUserResponse(raw as Record<string, unknown>)
    );
  },

  unblockUser(userId: number): Promise<UserProfile> {
    return request(`/api/v1/admin/users/${userId}/unblock`, { method: "POST" }).then((raw) =>
      mapUserResponse(raw as Record<string, unknown>)
    );
  },

  updateUserRole(userId: number, role: UserRole): Promise<UserProfile> {
    return request(`/api/v1/admin/users/${userId}/role`, {
      method: "PATCH",
      body: JSON.stringify({ role }),
    }).then((raw) => mapUserResponse(raw as Record<string, unknown>));
  },

  /* ── Admin: Orders ────────────────────────────────── */

  updateOrderStatus(orderId: number, status: OrderStatus, rejectionReason?: string): Promise<ExchangeOrder> {
    const payload: Record<string, unknown> = { status };
    if (rejectionReason !== undefined) payload.rejection_reason = rejectionReason;
    return request(`/api/v1/admin/orders/${orderId}/status`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }).then((raw) => mapOrderResponse(raw as Record<string, unknown>));
  },

  bulkModerateOrders(orderIds: number[], status: OrderStatus, rejectionReason?: string): Promise<ExchangeOrder[]> {
    const payload: Record<string, unknown> = { order_ids: orderIds, status };
    if (rejectionReason !== undefined) payload.rejection_reason = rejectionReason;
    return request("/api/v1/admin/orders/bulk-moderate", {
      method: "POST",
      body: JSON.stringify(payload),
    }).then((raw) => {
      const arr = raw as Record<string, unknown>[];
      return Array.isArray(arr) ? arr.map(mapOrderResponse) : [];
    });
  },

  /* ── Statistics ──────────────────────────────────── */

  getStatistics(dateFrom?: string, dateTo?: string): Promise<StatisticsData> {
    const params = new URLSearchParams();
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    const qs = params.toString();
    const path = qs ? `/api/v1/statistics?${qs}` : "/api/v1/statistics";
    return request(path).then((raw) => mapStatisticsResponse(raw as Record<string, unknown>));
  },

  /* ── Support ─────────────────────────────────────── */

  getTickets(): Promise<SupportTicket[]> {
    return request("/api/v1/support/tickets").then((raw) => {
      const arr = raw as Record<string, unknown>[];
      return Array.isArray(arr) ? arr.map(mapTicketResponse) : [];
    });
  },

  createTicket(subject: string, orderId?: number, message?: string): Promise<SupportTicket> {
    const payload: Record<string, unknown> = { subject };
    if (orderId !== undefined) payload.order_id = orderId;
    if (message !== undefined) payload.message = message;
    return request("/api/v1/support/tickets", {
      method: "POST",
      body: JSON.stringify(payload),
    }).then((raw) => mapTicketResponse(raw as Record<string, unknown>));
  },

  getTicketMessages(ticketId: number): Promise<SupportMessage[]> {
    return request(`/api/v1/support/tickets/${ticketId}/messages`).then((raw) => {
      const arr = raw as Record<string, unknown>[];
      return Array.isArray(arr) ? arr.map(mapMessageResponse) : [];
    });
  },

  sendMessage(ticketId: number, text: string): Promise<SupportMessage> {
    return request(`/api/v1/support/tickets/${ticketId}/messages`, {
      method: "POST",
      body: JSON.stringify({ text }),
    }).then((raw) => mapMessageResponse(raw as Record<string, unknown>));
  },

  closeTicket(ticketId: number): Promise<SupportTicket> {
    return request(`/api/v1/support/tickets/${ticketId}/close`, { method: "POST" }).then((raw) =>
      mapTicketResponse(raw as Record<string, unknown>)
    );
  },
};
