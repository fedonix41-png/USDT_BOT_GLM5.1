export type UserRole = "client" | "operator" | "admin" | "super_admin";

export interface UserProfile {
  id: number;
  telegram_id: number;
  username: string | null;
  full_name: string | null;
  role: UserRole;
  is_blocked: boolean;
  balance: number;
  fiat_balance: number;
  referrals_count: number;
  referral_earned: number;
  created_at: string;
}

export interface ExchangeOrder {
  id: number;
  user_id: number;
  order_type: "buy" | "sell";
  amount_usdt: number;
  rate: number;
  total_fiat: number;
  status: "pending" | "completed" | "cancelled";
  link_broken: boolean;
  client_details?: string;
  requisites_selected?: string;
  created_at: string;
  updated_at: string;
}

export interface SystemSettings {
  buy_rate: number;
  sell_rate: number;
  buy_enabled: boolean;
  sell_enabled: boolean;
  bot_enabled: boolean;
}

export interface SupportMessage {
  id: string;
  sender_id: number;
  sender_name: string;
  sender_role: UserRole;
  text: string;
  timestamp: string;
}

export interface SupportTicket {
  id: string;
  ticket_id: string;
  user_id: number;
  username: string;
  subject: string;
  order_id?: number;
  status: "open" | "closed";
  messages: SupportMessage[];
  created_at: string;
  updated_at: string;
}

export interface Statistics {
  total_orders: number;
  completed_orders: number;
  cancelled_orders: number;
  total_volume_usdt: number;
  total_volume_fiat: number;
  buy_orders: number;
  sell_orders: number;
}
