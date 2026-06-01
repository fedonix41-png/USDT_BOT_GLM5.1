"""Support router for API with Redis storage persistence and multi-role views."""

import json
import logging
import time
from datetime import datetime

from aiohttp import web

from app.api.deps import get_current_user
from app.api.exceptions import NotFoundError, ValidationError as APIValidationError
from app.config import settings
from app.database.engine import async_session_maker
from app.database.models.user import RoleEnum, User
from app.repositories.user_repo import UserRepository
from app.utils.redis import get_redis

logger = logging.getLogger(__name__)
router = web.RouteTableDef()


async def get_user_tickets(user_id: int) -> list[dict]:
    """Get all tickets for a specific user from Redis."""
    redis = await get_redis()
    key = f"support_tickets:{user_id}"
    data = await redis.get(key)
    if not data:
        return []
    try:
        return json.loads(data)
    except Exception as e:
        logger.error(f"Failed to parse support tickets from Redis: {e}")
        return []


async def save_user_tickets(user_id: int, tickets: list[dict]) -> None:
    """Save all tickets for a specific user to Redis."""
    redis = await get_redis()
    key = f"support_tickets:{user_id}"
    await redis.set(key, json.dumps(tickets))


@router.get("/api/v1/support/tickets")
async def list_support_tickets(request: web.Request) -> web.Response:
    """List support tickets. Clients see only their own; staff see all tickets."""
    current_user = await get_current_user(request)

    if current_user.role in (RoleEnum.operator, RoleEnum.admin, RoleEnum.super_admin):
        # Staff role: scan all support keys in Redis and aggregate all tickets
        redis = await get_redis()
        try:
            keys = await redis.keys("support_tickets:*")
        except Exception as e:
            logger.error(f"Failed to list support ticket keys from Redis: {e}")
            return web.json_response([])

        all_tickets = []
        for key in keys:
            data = await redis.get(key)
            if data:
                try:
                    tickets_list = json.loads(data)
                    all_tickets.extend(tickets_list)
                except Exception as e:
                    logger.error(f"Failed to parse tickets for key {key}: {e}")
        
        # Sort combined tickets by update timestamp (newest first)
        all_tickets.sort(key=lambda t: t.get("updated_at", ""), reverse=True)
        return web.json_response(all_tickets)

    # Client role: return user's own tickets
    tickets = await get_user_tickets(current_user.id)
    return web.json_response(tickets)


@router.post("/api/v1/support/tickets")
async def create_support_ticket(request: web.Request) -> web.Response:
    """Create a support ticket, save it in Redis, and notify Telegram operators."""
    current_user = await get_current_user(request)

    try:
        body_text = request.get("body_text", "")
        if not body_text:
            body_text = await request.text()
        data = json.loads(body_text) if body_text else {}
    except json.JSONDecodeError:
        raise APIValidationError("Invalid JSON body")

    subject = data.get("subject", "General")
    message_text = data.get("message", "")
    order_id = data.get("order_id")

    if not message_text:
        raise APIValidationError("Message text is required")

    # Generate a unique ticket ID using timestamp
    ticket_id = int(time.time() * 10)

    now_str = datetime.utcnow().isoformat() + "Z"
    username = current_user.username or "N/A"
    sender_name = current_user.full_name or username or "Клиент"

    ticket = {
        "id": ticket_id,
        "user_id": current_user.id,
        "subject": subject,
        "order_id": order_id,
        "status": "open",
        "messages": [
            {
                "id": 1,
                "sender_id": current_user.id,
                "sender_name": sender_name,
                "sender_role": "client",
                "text": message_text,
                "created_at": now_str,
            }
        ],
        "created_at": now_str,
        "updated_at": now_str,
    }

    # Save to Redis
    tickets = await get_user_tickets(current_user.id)
    tickets.append(ticket)
    await save_user_tickets(current_user.id, tickets)

    # Send Telegram notification to operators
    from aiogram import Bot
    from app.services.notification_service import NotificationService

    order_info = f" (по сделке #{order_id})" if order_id else ""
    text = (
        f"📩 [Тикет #{ticket_id}] Обращение в поддержку от @{username} (ID: {current_user.telegram_id}){order_info}:\n"
        f"Тема: {subject}\n"
        f"Сообщение: {message_text}"
    )

    async with async_session_maker() as session:
        try:
            async with Bot(token=settings.BOT_TOKEN) as bot:
                notif_service = NotificationService(session)
                await notif_service.send_to_all_chats(bot, text)
            logger.info(f"Support message for ticket #{ticket_id} sent to Telegram")
        except Exception as e:
            logger.error(f"Failed to send support message to Telegram: {e}")

    return web.json_response(ticket, status=201)


@router.get("/api/v1/support/tickets/{ticket_id}/messages")
async def get_ticket_messages(request: web.Request) -> web.Response:
    """Get all messages for a specific support ticket."""
    current_user = await get_current_user(request)
    ticket_id = int(request.match_info["ticket_id"])

    # Scan keys to find the ticket globally (allowing operators to read any ticket)
    redis = await get_redis()
    keys = await redis.keys("support_tickets:*")
    target_ticket = None

    for key in keys:
        data = await redis.get(key)
        if data:
            try:
                tickets_list = json.loads(data)
                for t in tickets_list:
                    if t["id"] == ticket_id:
                        # Verify access: client can only read their own tickets
                        if current_user.role == RoleEnum.client and t["user_id"] != current_user.id:
                            continue
                        target_ticket = t
                        break
            except Exception:
                pass
        if target_ticket:
            break

    if not target_ticket:
        raise NotFoundError("Support ticket not found")

    return web.json_response(target_ticket["messages"])


@router.post("/api/v1/support/tickets/{ticket_id}/messages")
async def send_ticket_message(request: web.Request) -> web.Response:
    """Send a reply inside an active support ticket (handles both client and staff)."""
    current_user = await get_current_user(request)
    ticket_id = int(request.match_info["ticket_id"])

    try:
        body_text = request.get("body_text", "")
        if not body_text:
            body_text = await request.text()
        data = json.loads(body_text) if body_text else {}
    except json.JSONDecodeError:
        raise APIValidationError("Invalid JSON body")

    text = data.get("text", "")
    if not text:
        raise APIValidationError("Message text is required")

    # Scan all keys to find the ticket universally
    redis = await get_redis()
    keys = await redis.keys("support_tickets:*")
    target_ticket = None
    target_key = None
    target_tickets_list = None

    for key in keys:
        data = await redis.get(key)
        if data:
            try:
                tickets_list = json.loads(data)
                for t in tickets_list:
                    if t["id"] == ticket_id:
                        # Clients can only reply to their own tickets
                        if current_user.role == RoleEnum.client and t["user_id"] != current_user.id:
                            continue
                        target_ticket = t
                        target_key = key
                        target_tickets_list = tickets_list
                        break
            except Exception:
                pass
        if target_ticket:
            break

    if not target_ticket:
        raise NotFoundError("Support ticket not found")

    now_str = datetime.utcnow().isoformat() + "Z"
    username = current_user.username or "N/A"
    sender_name = current_user.full_name or username or "Сотрудник" if current_user.role != RoleEnum.client else "Клиент"

    new_msg = {
        "id": len(target_ticket["messages"]) + 1,
        "sender_id": current_user.id,
        "sender_name": sender_name,
        "sender_role": current_user.role.value,
        "text": text,
        "created_at": now_str,
    }

    target_ticket["messages"].append(new_msg)
    target_ticket["updated_at"] = now_str
    
    # Save the updated list back to the specific user's key
    owner_user_id = target_ticket["user_id"]
    await save_user_tickets(owner_user_id, target_tickets_list)

    # Send alerts based on who replied
    from aiogram import Bot
    from app.services.notification_service import NotificationService

    async with async_session_maker() as session:
        if current_user.role in (RoleEnum.operator, RoleEnum.admin, RoleEnum.super_admin):
            # Staff replied: send private Telegram DM to the client (owner of the ticket)
            user_repo = UserRepository(session)
            client_user = await user_repo.get_by_id(owner_user_id)
            if client_user and client_user.telegram_id:
                try:
                    async with Bot(token=settings.BOT_TOKEN) as bot:
                        client_alert = (
                            f"✉️ Получен ответ от поддержки по вашему обращению #{ticket_id} (Тема: {target_ticket['subject']}):\n\n"
                            f"« {text} »\n\n"
                            f"Вы можете ответить на это сообщение внутри нашего приложения Web3 App."
                        )
                        await bot.send_message(chat_id=client_user.telegram_id, text=client_alert)
                    logger.info(f"Direct message notification sent to client {client_user.telegram_id} for ticket #{ticket_id}")
                except Exception as e:
                    logger.error(f"Failed to send ticket reply DM to client {client_user.telegram_id}: {e}")
        else:
            # Client replied: send Telegram alert to all operators/admins
            try:
                async with Bot(token=settings.BOT_TOKEN) as bot:
                    notif_service = NotificationService(session)
                    alert_text = (
                        f"💬 [Тикет #{ticket_id}] Новый ответ от клиента @{username} (ID: {current_user.telegram_id}):\n"
                        f"Тема: {target_ticket['subject']}\n"
                        f"Сообщение: {text}"
                    )
                    await notif_service.send_to_all_chats(bot, alert_text)
            except Exception as e:
                logger.error(f"Failed to send client ticket reply alert to staff Telegram: {e}")

    return web.json_response(new_msg, status=201)


@router.post("/api/v1/support/tickets/{ticket_id}/close")
async def close_ticket(request: web.Request) -> web.Response:
    """Close an active support ticket."""
    current_user = await get_current_user(request)
    ticket_id = int(request.match_info["ticket_id"])

    # Scan keys to find the ticket globally
    redis = await get_redis()
    keys = await redis.keys("support_tickets:*")
    target_ticket = None
    target_tickets_list = None

    for key in keys:
        data = await redis.get(key)
        if data:
            try:
                tickets_list = json.loads(data)
                for t in tickets_list:
                    if t["id"] == ticket_id:
                        if current_user.role == RoleEnum.client and t["user_id"] != current_user.id:
                            continue
                        target_ticket = t
                        target_tickets_list = tickets_list
                        break
            except Exception:
                pass
        if target_ticket:
            break

    if not target_ticket:
        raise NotFoundError("Support ticket not found")

    target_ticket["status"] = "closed"
    target_ticket["updated_at"] = datetime.utcnow().isoformat() + "Z"
    
    owner_user_id = target_ticket["user_id"]
    await save_user_tickets(owner_user_id, target_tickets_list)

    # Forward to operators or notify client depending on who closed it
    from aiogram import Bot
    from app.services.notification_service import NotificationService

    username = current_user.username or "N/A"
    
    async with async_session_maker() as session:
        if current_user.role in (RoleEnum.operator, RoleEnum.admin, RoleEnum.super_admin):
            # Staff closed it: send Telegram DM to client
            user_repo = UserRepository(session)
            client_user = await user_repo.get_by_id(owner_user_id)
            if client_user and client_user.telegram_id:
                try:
                    async with Bot(token=settings.BOT_TOKEN) as bot:
                        await bot.send_message(
                            chat_id=client_user.telegram_id,
                            text=f"🔒 Ваш тикет поддержки #{ticket_id} (Тема: {target_ticket['subject']}) был закрыт сотрудником техподдержки."
                        )
                except Exception as e:
                    logger.error(f"Failed to send ticket closure DM to client: {e}")
        else:
            # Client closed it: notify staff
            try:
                async with Bot(token=settings.BOT_TOKEN) as bot:
                    notif_service = NotificationService(session)
                    alert_text = (
                        f"🔒 [Тикет #{ticket_id}] Клиент @{username} закрыл обращение.\n"
                        f"Тема: {target_ticket['subject']}"
                    )
                    await notif_service.send_to_all_chats(bot, alert_text)
            except Exception as e:
                logger.error(f"Failed to send ticket closed alert to Telegram: {e}")

    return web.json_response(target_ticket)
