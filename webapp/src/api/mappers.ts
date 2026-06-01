import type {
  UserProfile,
  ExchangeOrder,
  SystemSettings,
  SupportTicket,
  SupportMessage,
  StatisticsData,
  OrderCreateRequest,
} from "../types";

export function mapUserResponse(data: Record<string, unknown>): UserProfile {
  return {
    id: (data.id as number) ?? 0,
    telegramId: (data.telegram_id as number) ?? 0,
    username: (data.username as string) ?? "",
    fullName: (data.full_name as string) ?? "",
    role: (data.role as UserProfile["role"]) ?? "client",
    isBlocked: (data.is_blocked as boolean) ?? false,
    balance: Number(data.balance) || 0,
    fiatBalance: Number(data.fiat_balance) || 0,
    referralsCount: (data.referrals_count as number) ?? 0,
    referralEarned: Number(data.referral_earned) || 0,
    createdAt: (data.created_at as string) ?? "",
  };
}

export function mapOrderResponse(data: Record<string, unknown>): ExchangeOrder {
  return {
    id: (data.id as number) ?? 0,
    userId: (data.user_id as number) ?? 0,
    username: (data.username as string) ?? "",
    orderType: (data.order_type as ExchangeOrder["orderType"]) ?? "buy",
    amountUsdt: Number(data.amount_usdt) || 0,
    rate: Number(data.rate) || 0,
    totalFiat: Number(data.total_fiat) || 0,
    status: (data.status as ExchangeOrder["status"]) ?? "created",
    paymentLinkSnapshot: (data.payment_link_snapshot as string) ?? "",
    isPaidFromBalance: (data.is_paid_from_balance as boolean) ?? false,
    linkBroken: (data.link_broken as boolean) ?? false,
    rejectionReason: (data.rejection_reason as string | null) ?? null,
    createdAt: (data.created_at as string) ?? "",
    updatedAt: (data.updated_at as string) ?? "",
  };
}

export function mapSettingsResponse(data: Record<string, unknown>): SystemSettings {
  return {
    buyRate: Number(data.buy_rate) || 0,
    sellRate: Number(data.sell_rate) || 0,
    buyEnabled: (data.buy_enabled as boolean) ?? true,
    sellEnabled: (data.sell_enabled as boolean) ?? true,
    botEnabled: (data.bot_enabled as boolean) ?? true,
    requisitesCard: (data.requisites_card as string) ?? "",
    requisitesWallet: (data.requisites_wallet as string) ?? "",
    notificationChats: Array.isArray(data.notification_chats)
      ? (data.notification_chats as string[])
      : [],
  };
}

export function mapMessageResponse(data: Record<string, unknown>): SupportMessage {
  return {
    id: (data.id as number) ?? 0,
    senderId: (data.sender_id as number) ?? 0,
    senderName: (data.sender_name as string) ?? "",
    senderRole: (data.sender_role as SupportMessage["senderRole"]) ?? "client",
    text: (data.text as string) ?? "",
    createdAt: (data.created_at as string) ?? "",
  };
}

export function mapTicketResponse(data: Record<string, unknown>): SupportTicket {
  return {
    id: (data.id as number) ?? 0,
    userId: (data.user_id as number) ?? 0,
    subject: (data.subject as string) ?? "",
    orderId: (data.order_id as number | null) ?? null,
    status: (data.status as SupportTicket["status"]) ?? "open",
    messages: Array.isArray(data.messages)
      ? (data.messages as Record<string, unknown>[]).map(mapMessageResponse)
      : [],
    createdAt: (data.created_at as string) ?? "",
    updatedAt: (data.updated_at as string) ?? "",
  };
}

export function mapStatisticsResponse(data: Record<string, unknown>): StatisticsData {
  return {
    totalOrders: (data.total_orders as number) ?? 0,
    completedOrders: (data.completed_orders as number) ?? 0,
    cancelledOrders: (data.cancelled_orders as number) ?? 0,
    totalVolumeUsdt: Number(data.total_volume_usdt) || 0,
    totalVolumeFiat: Number(data.total_volume_fiat) || 0,
    buyOrders: (data.buy_orders as number) ?? 0,
    sellOrders: (data.sell_orders as number) ?? 0,
  };
}

export function toOrderCreatePayload(body: OrderCreateRequest): Record<string, unknown> {
  return {
    order_type: body.orderType,
    amount_usdt: body.amountUsdt,
    client_details: body.clientDetails,
  };
}
