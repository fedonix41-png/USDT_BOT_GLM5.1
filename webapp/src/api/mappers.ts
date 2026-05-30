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
    balance: (data.balance as number) ?? 0,
    fiatBalance: (data.fiat_balance as number) ?? 0,
    referralsCount: (data.referrals_count as number) ?? 0,
    referralEarned: (data.referral_earned as number) ?? 0,
    createdAt: (data.created_at as string) ?? "",
  };
}

export function mapOrderResponse(data: Record<string, unknown>): ExchangeOrder {
  return {
    id: (data.id as number) ?? 0,
    userId: (data.user_id as number) ?? 0,
    username: (data.username as string) ?? "",
    orderType: (data.order_type as ExchangeOrder["orderType"]) ?? "buy",
    amountUsdt: (data.amount_usdt as number) ?? 0,
    rate: (data.rate as number) ?? 0,
    totalFiat: (data.total_fiat as number) ?? 0,
    status: (data.status as ExchangeOrder["status"]) ?? "created",
    paymentLinkSnapshot: (data.payment_link_snapshot as string) ?? "",
    linkBroken: (data.link_broken as boolean) ?? false,
    rejectionReason: (data.rejection_reason as string | null) ?? null,
    createdAt: (data.created_at as string) ?? "",
    updatedAt: (data.updated_at as string) ?? "",
  };
}

export function mapSettingsResponse(data: Record<string, unknown>): SystemSettings {
  return {
    buyRate: (data.buy_rate as number) ?? 0,
    sellRate: (data.sell_rate as number) ?? 0,
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
    totalVolumeUsdt: (data.total_volume_usdt as number) ?? 0,
    totalVolumeFiat: (data.total_volume_fiat as number) ?? 0,
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
