export type UserRole = "client" | "operator" | "admin" | "super_admin";

export interface UserProfile {
  id: number;
  username: string;
  role: UserRole;
  balance: number;
  fiatBalance: number;
  status: "active" | "frozen";
  referredBy?: string;
  referralsCount: number;
  referralEarned: number;
}

export interface ExchangeOrder {
  id: string;
  username: string;
  userId: number;
  type: "buy" | "sell";
  amountUsdt: number;
  amountRub: number;
  rate: number;
  clientDetails: string;
  requisitesSelected: string;
  status: "pending" | "completed" | "rejected";
  timestamp: string;
  rejectionReason?: string;
  complained?: boolean;
}

export interface SystemSettings {
  buyRate: number;
  sellRate: number;
  buyEnabled: boolean;
  sellEnabled: boolean;
  botEnabled: boolean;
  requisitesCard: string;
  requisitesWallet: string;
  notificationChats: string[];
}

export interface SupportMessage {
  id: string;
  senderId: number;
  senderName: string;
  senderRole: UserRole;
  text: string;
  timestamp: string;
}

export interface SupportTicket {
  id: string;
  userId: number;
  username: string;
  subject: string;
  orderId?: string;
  status: "open" | "closed";
  messages: SupportMessage[];
  createdAt: string;
  updatedAt: string;
}

export interface AuthState {
  token: string | null;
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  orders: ExchangeOrder[];
  settings: SystemSettings | null;
  hapticLogs: { text: string; time: string; type: "light" | "success" | "error" }[];
  setAuth: (token: string, user: UserProfile) => void;
  logout: () => void;
  setLoading: (status: boolean) => void;
  setOrders: (orders: ExchangeOrder[]) => void;
  setSettings: (settings: SystemSettings) => void;
  addHapticLog: (text: string, type: "light" | "success" | "error") => void;
  clearHapticLogs: () => void;
  updateUserBalance: (newBalance: number) => void;
  refreshUserData: () => Promise<void>;
}
