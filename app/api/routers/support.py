"""Support router for API with Redis storage persistence."""

import json
import logging
import time
from datetime import datetime

from aiohttp import web

from app.api.deps import get_current_user
from app.api.exceptions import NotFoundError, ValidationError as APIValidationError
from app.config import settings
from app.database.engine import async_session_maker
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
    """List support tickets stored in Redis for the current user."""
    current_user = await get_current_user(request)
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

    tickets = await get_user_tickets(current_user.id)
    ticket = next((t for t in tickets if t["id"] == ticket_id), None)
    if not ticket:
        raise NotFoundError("Support ticket not found")

    return web.json_response(ticket["messages"])


@router.post("/api/v1/support/tickets/{ticket_id}/messages")
async def send_ticket_message(request: web.Request) -> web.Response:
    """Send a reply inside an active support ticket."""
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

    tickets = await get_user_tickets(current_user.id)
    ticket = next((t for t in tickets if t["id"] == ticket_id), None)
    if not ticket:
        raise NotFoundError("Support ticket not found")

    now_str = datetime.utcnow().isoformat() + "Z"
    username = current_user.username or "N/A"
    sender_name = current_user.full_name or username or "Клиент"

    new_msg = {
        "id": len(ticket["messages"]) + 1,
        "sender_id": current_user.id,
        "sender_name": sender_name,
        "sender_role": "client",
        "text": text,
        "created_at": now_str,
    }

    ticket["messages"].append(new_msg)
    ticket["updated_at"] = now_str
    await save_user_tickets(current_user.id, tickets)

    # Forward reply to operators in Telegram
    from aiogram import Bot
    from app.services.notification_service import NotificationService

    alert_text = (
        f"💬 [Тикет #{ticket_id}] Ответ от клиента @{username} (ID: {current_user.telegram_id}):\n"
        f"Тема: {ticket['subject']}\n"
        f"Сообщение: {text}"
    )

    async with async_session_maker() as session:
        try:
            async with Bot(token=settings.BOT_TOKEN) as bot:
                notif_service = NotificationService(session)
                await notif_service.send_to_all_chats(bot, alert_text)
            logger.info(f"Support reply for ticket #{ticket_id} sent to Telegram")
        except Exception as e:
            logger.error(f"Failed to send support reply to Telegram: {e}")

    return web.json_response(new_msg, status=201)


@router.post("/api/v1/support/tickets/{ticket_id}/close")
async def close_ticket(request: web.Request) -> web.Response:
    """Close an active support ticket."""
    current_user = await get_current_user(request)
    ticket_id = int(request.match_info["ticket_id"])

    tickets = await get_user_tickets(current_user.id)
    ticket = next((t for t in tickets if t["id"] == ticket_id), None)
    if not ticket:
        raise NotFoundError("Support ticket not found")

    ticket["status"] = "closed"
    ticket["updated_at"] = datetime.utcnow().isoformat() + "Z"
    await save_user_tickets(current_user.id, tickets)

    # Forward to operators in Telegram
    from aiogram import Bot
    from app.services.notification_service import NotificationService

    username = current_user.username or "N/A"
    alert_text = (
        f"🔒 [Тикет #{ticket_id}] Клиент @{username} закрыл обращение.\n"
        f"Тема: {ticket['subject']}"
    )

    async with async_session_maker() as session:
        try:
            async with Bot(token=settings.BOT_TOKEN) as bot:
                notif_service = NotificationService(session)
                await notif_service.send_to_all_chats(bot, alert_text)
        except Exception as e:
            logger.error(f"Failed to send ticket closed alert to Telegram: {e}")

    return web.json_response(ticket)
