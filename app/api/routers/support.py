"""Support router for API with PostgreSQL persistence and multi-role views."""

import json
import logging
from datetime import datetime

from aiohttp import web
from sqlalchemy import select

from app.api.deps import get_current_user
from app.api.exceptions import NotFoundError
from app.api.exceptions import ValidationError as APIValidationError
from app.config import settings
from app.database.engine import async_session_maker
from app.database.models.support import SupportMessage, SupportTicket
from app.database.models.user import RoleEnum
from app.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)
router = web.RouteTableDef()


def ticket_to_dict(ticket: SupportTicket) -> dict:
    """Serialize a SupportTicket model to a frontend-compatible dict."""
    return {
        "id": ticket.id,
        "user_id": ticket.user_id,
        "subject": ticket.subject,
        "order_id": ticket.order_id,
        "status": ticket.status,
        "messages": [
            {
                "id": msg.id,
                "sender_id": msg.sender_id,
                "sender_name": msg.sender_name,
                "sender_role": msg.sender_role,
                "text": msg.text,
                "created_at": msg.created_at.isoformat() + "Z" if msg.created_at else None,
            }
            for msg in ticket.messages
        ],
        "created_at": ticket.created_at.isoformat() + "Z" if ticket.created_at else None,
        "updated_at": ticket.updated_at.isoformat() + "Z" if ticket.updated_at else None,
    }


@router.get("/api/v1/support/tickets")
async def list_support_tickets(request: web.Request) -> web.Response:
    """List support tickets. Clients see only their own; staff see all tickets."""
    current_user = await get_current_user(request)

    async with async_session_maker() as session:
        if current_user.role in (RoleEnum.operator, RoleEnum.admin, RoleEnum.super_admin):
            # Staff role: see all tickets
            stmt = select(SupportTicket).order_by(SupportTicket.updated_at.desc())
            result = await session.execute(stmt)
            tickets = result.scalars().all()
            return web.json_response([ticket_to_dict(t) for t in tickets])

        # Client role: see their own tickets
        stmt = (
            select(SupportTicket)
            .where(SupportTicket.user_id == current_user.id)
            .order_by(SupportTicket.updated_at.desc())
        )
        result = await session.execute(stmt)
        tickets = result.scalars().all()
        return web.json_response([ticket_to_dict(t) for t in tickets])


@router.post("/api/v1/support/tickets")
async def create_support_ticket(request: web.Request) -> web.Response:
    """Create a support ticket in PostgreSQL and notify Telegram operators."""
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

    username = current_user.username or "N/A"
    sender_name = current_user.full_name or username or "Клиент"

    async with async_session_maker() as session:
        # Create ticket
        ticket = SupportTicket(
            user_id=current_user.id,
            subject=subject,
            order_id=order_id,
            status="open",
        )
        session.add(ticket)
        await session.flush()

        # Create first message
        first_msg = SupportMessage(
            ticket_id=ticket.id,
            sender_id=current_user.id,
            sender_name=sender_name,
            sender_role="client",
            text=message_text,
        )
        session.add(first_msg)
        await session.commit()

        # Load completely with relationships populated
        stmt = select(SupportTicket).where(SupportTicket.id == ticket.id)
        result = await session.execute(stmt)
        ticket = result.scalar_one()
        ticket_dict = ticket_to_dict(ticket)

    # Send Telegram notification to operators
    from aiogram import Bot

    from app.services.notification_service import NotificationService

    order_info = f" (по сделке #{order_id})" if order_id else ""
    text = (
        f"📩 [Тикет #{ticket.id}] Обращение в поддержку от @{username} (ID: {current_user.telegram_id}){order_info}:\n"
        f"Тема: {subject}\n"
        f"Сообщение: {message_text}"
    )

    async with async_session_maker() as session:
        try:
            async with Bot(token=settings.BOT_TOKEN) as bot:
                notif_service = NotificationService(session)
                await notif_service.send_to_all_chats(bot, text)
            logger.info(f"Support message for ticket #{ticket.id} sent to Telegram")
        except Exception as e:
            logger.error(f"Failed to send support message to Telegram: {e}")

    return web.json_response(ticket_dict, status=201)


@router.get("/api/v1/support/tickets/{ticket_id}/messages")
async def get_ticket_messages(request: web.Request) -> web.Response:
    """Get all messages for a specific support ticket."""
    current_user = await get_current_user(request)
    ticket_id = int(request.match_info["ticket_id"])

    async with async_session_maker() as session:
        stmt = select(SupportTicket).where(SupportTicket.id == ticket_id)
        result = await session.execute(stmt)
        ticket = result.scalar_one_or_none()

        if not ticket:
            raise NotFoundError("Support ticket not found")

        # Verify access: client can only read their own tickets
        if current_user.role == RoleEnum.client and ticket.user_id != current_user.id:
            raise NotFoundError("Support ticket not found")

        messages = [
            {
                "id": msg.id,
                "sender_id": msg.sender_id,
                "sender_name": msg.sender_name,
                "sender_role": msg.sender_role,
                "text": msg.text,
                "created_at": msg.created_at.isoformat() + "Z" if msg.created_at else None,
            }
            for msg in ticket.messages
        ]

    return web.json_response(messages)


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

    username = current_user.username or "N/A"
    sender_name = current_user.full_name or username or (
        "Сотрудник" if current_user.role != RoleEnum.client else "Клиент"
    )

    async with async_session_maker() as session:
        stmt = select(SupportTicket).where(SupportTicket.id == ticket_id)
        result = await session.execute(stmt)
        ticket = result.scalar_one_or_none()

        if not ticket:
            raise NotFoundError("Support ticket not found")

        # Clients can only reply to their own tickets
        if current_user.role == RoleEnum.client and ticket.user_id != current_user.id:
            raise NotFoundError("Support ticket not found")

        new_msg = SupportMessage(
            ticket_id=ticket.id,
            sender_id=current_user.id,
            sender_name=sender_name,
            sender_role=current_user.role.value,
            text=text,
        )
        session.add(new_msg)

        # Mark ticket as open and update the timestamp
        ticket.status = "open"
        ticket.updated_at = datetime.utcnow()
        await session.commit()

        # Load fresh message object to serialize
        stmt_msg = select(SupportMessage).where(SupportMessage.id == new_msg.id)
        res_msg = await session.execute(stmt_msg)
        msg_obj = res_msg.scalar_one()

        response_data = {
            "id": msg_obj.id,
            "sender_id": msg_obj.sender_id,
            "sender_name": msg_obj.sender_name,
            "sender_role": msg_obj.sender_role,
            "text": msg_obj.text,
            "created_at": msg_obj.created_at.isoformat() + "Z" if msg_obj.created_at else None,
        }
        owner_user_id = ticket.user_id
        subject = ticket.subject

    # Send alerts based on who replied
    from aiogram import Bot

    from app.services.notification_service import NotificationService

    async with async_session_maker() as session:
        if current_user.role in (RoleEnum.operator, RoleEnum.admin, RoleEnum.super_admin):
            # Staff replied: send private Telegram DM to the client
            user_repo = UserRepository(session)
            client_user = await user_repo.get_by_id(owner_user_id)
            if client_user and client_user.telegram_id:
                try:
                    async with Bot(token=settings.BOT_TOKEN) as bot:
                        client_alert = (
                            f"✉️ Получен ответ от поддержки по вашему обращению #{ticket_id} (Тема: {subject}):\n\n"
                            f"« {text} »\n\n"
                            f"Вы можете ответить на это сообщение внутри нашего приложения Web3 App."
                        )
                        await bot.send_message(chat_id=client_user.telegram_id, text=client_alert)
                    logger.info(
                        f"Direct message notification sent to client {client_user.telegram_id} for ticket #{ticket_id}"
                    )
                except Exception as e:
                    logger.error(f"Failed to send ticket reply DM to client {client_user.telegram_id}: {e}")
        else:
            # Client replied: send Telegram alert to all operators/admins
            try:
                async with Bot(token=settings.BOT_TOKEN) as bot:
                    notif_service = NotificationService(session)
                    alert_text = (
                        f"💬 [Тикет #{ticket_id}] Новый ответ от клиента @{username} "
                        f"(ID: {current_user.telegram_id}):\n"
                        f"Тема: {subject}\n"
                        f"Сообщение: {text}"
                    )
                    await notif_service.send_to_all_chats(bot, alert_text)
            except Exception as e:
                logger.error(f"Failed to send client ticket reply alert to staff Telegram: {e}")

    return web.json_response(response_data, status=201)


@router.post("/api/v1/support/tickets/{ticket_id}/close")
async def close_ticket(request: web.Request) -> web.Response:
    """Close an active support ticket."""
    current_user = await get_current_user(request)
    ticket_id = int(request.match_info["ticket_id"])

    async with async_session_maker() as session:
        stmt = select(SupportTicket).where(SupportTicket.id == ticket_id)
        result = await session.execute(stmt)
        ticket = result.scalar_one_or_none()

        if not ticket:
            raise NotFoundError("Support ticket not found")

        if current_user.role == RoleEnum.client and ticket.user_id != current_user.id:
            raise NotFoundError("Support ticket not found")

        ticket.status = "closed"
        ticket.updated_at = datetime.utcnow()
        await session.commit()

        # Load fresh for serialization
        stmt = select(SupportTicket).where(SupportTicket.id == ticket_id)
        result = await session.execute(stmt)
        ticket = result.scalar_one()
        ticket_dict = ticket_to_dict(ticket)
        owner_user_id = ticket.user_id
        subject = ticket.subject

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
                            text=(
                                f"🔒 Ваш тикет поддержки #{ticket_id} (Тема: {subject}) "
                                f"был закрыт сотрудником техподдержки."
                            ),
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
                        f"Тема: {subject}"
                    )
                    await notif_service.send_to_all_chats(bot, alert_text)
            except Exception as e:
                logger.error(f"Failed to send ticket closed alert to Telegram: {e}")

    return web.json_response(ticket_dict)
