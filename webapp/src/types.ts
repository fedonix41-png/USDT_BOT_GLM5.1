/** User role enum matching backend values */
export type UserRole = "client" | "operator" | "admin" | "super_admin";

/** Order type enum */
export type OrderType = "buy" | "sell";

/** Order status matching backend: "created" | "completed" | "cancelled" */
export type OrderStatus = "created" | "completed" | "cancelled";

/** Ticket status */
export type TicketStatus = "open" | "closed";

/** Computed user status derived from isBlocked */
export type UserAccountStatus = "active" | "blocked";

/**
 * User profile — camelCase mirror of backend UserResponse.
 * Backend field `is_blocked` maps to `isBlocked`; use `getUserAccountStatus()` for the derived status.
 */
export interface UserProfile {
  /** Primary key */
  id: number;
  /** Telegram user ID */
  telegramId: number;
  /** Telegram @username (may be empty string) */
  username: string;
  /** Display name from Telegram */
  fullName: string;
  /** Authorization role */
  role: UserRole;
  /** Whether the user is blocked by an admin */
  isBlocked: boolean;
  /** USDT balance */
  balance: number;
  /** Fiat (RUB) balance */
  fiatBalance: number;
  /** Number of referrals made */
  referralsCount: number;
  /** Total USDT earned from referrals */
  referralEarned: number;
  /** ISO timestamp of registration */
  createdAt: string;
}

/**
 * Exchange order — camelCase mirror of backend OrderResponse.
 * `id` is a number (backend integer, not string).
 */
export interface ExchangeOrder {
  /** Primary key (integer) */
  id: number;
  /** FK to user */
  userId: number;
  /** Username included via backend join (may be empty) */
  username: string;
  /** "buy" or "sell" */
  orderType: OrderType;
  /** USDT amount */
  amountUsdt: number;
  /** Exchange rate */
  rate: number;
  /** Computed fiat total */
  totalFiat: number;
  /** "created" | "completed" | "cancelled" */
  status: OrderStatus;
  /** Saved payment link / requisites at order time */
  paymentLinkSnapshot: string;
  /** Whether the payment link was flagged as broken */
  linkBroken: boolean;
  /** Reason if cancelled by admin */
  rejectionReason: string | null;
  /** ISO timestamp of creation */
  createdAt: string;
  /** ISO timestamp of last update */
  updatedAt: string;
}

/**
 * System exchange settings — camelCase mirror of backend ExchangeSettings.
 */
export interface SystemSettings {
  /** Buy rate (RUB per USDT) */
  buyRate: number;
  /** Sell rate (RUB per USDT) */
  sellRate: number;
  /** Whether buy orders are accepted */
  buyEnabled: boolean;
  /** Whether sell orders are accepted */
  sellEnabled: boolean;
  /** Global bot on/off switch */
  botEnabled: boolean;
  /** Bank card requisites shown to users */
  requisitesCard: string;
  /** USDT TRC-20 wallet address */
  requisitesWallet: string;
  /** Telegram chat IDs for notifications */
  notificationChats: string[];
}

/**
 * Support message inside a ticket.
 */
export interface SupportMessage {
  /** Primary key */
  id: number;
  /** Sender user ID */
  senderId: number;
  /** Sender display name */
  senderName: string;
  /** Sender role at time of sending */
  senderRole: UserRole;
  /** Message body */
  text: string;
  /** ISO timestamp */
  createdAt: string;
}

/**
 * Support ticket with embedded messages.
 */
export interface SupportTicket {
  /** Primary key */
  id: number;
  /** Owner user ID */
  userId: number;
  /** Short description */
  subject: string;
  /** Related order ID (nullable) */
  orderId: number | null;
  /** "open" or "closed" */
  status: TicketStatus;
  /** Thread of messages */
  messages: SupportMessage[];
  /** ISO timestamp of creation */
  createdAt: string;
  /** ISO timestamp of last update */
  updatedAt: string;
}

/**
 * Request body for creating an order (camelCase from frontend).
 * Will be converted to snake_case before sending to backend.
 */
export interface OrderCreateRequest {
  orderType: OrderType;
  amountUsdt: number;
  clientDetails: string;
}

/**
 * Admin statistics — camelCase mirror of backend StatisticsResponse.
 */
export interface StatisticsData {
  totalOrders: number;
  completedOrders: number;
  cancelledOrders: number;
  totalVolumeUsdt: number;
  totalVolumeFiat: number;
  buyOrders: number;
  sellOrders: number;
}

/**
 * Toast notification for UI feedback.
 */
export interface ToastMessage {
  id: string;
  text: string;
  type: "success" | "error" | "info";
  duration?: number;
}

/**
 * Auth & global app state stored in Zustand.
 */
export interface AuthState {
  token: string | null;
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  orders: ExchangeOrder[];
  settings: SystemSettings | null;
  tickets: SupportTicket[];
  hapticLogs: { text: string; time: string; type: "light" | "success" | "error" }[];
  setAuth: (token: string, user: UserProfile) => void;
  logout: () => void;
  setLoading: (status: boolean) => void;
  setOrders: (orders: ExchangeOrder[]) => void;
  setSettings: (settings: SystemSettings) => void;
  setTickets: (tickets: SupportTicket[]) => void;
  addHapticLog: (text: string, type: "light" | "success" | "error") => void;
  clearHapticLogs: () => void;
  updateUserBalance: (newBalance: number) => void;
  refreshUserData: () => Promise<void>;
}

/** Derive a display-friendly account status from UserProfile */
export function getUserAccountStatus(user: UserProfile): UserAccountStatus {
  return user.isBlocked ? "blocked" : "active";
}
