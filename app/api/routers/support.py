"""Support router for API with PostgreSQL persistence and multi-role views."""

import logging
from datetime import datetime, UTC

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.api.exceptions import NotFoundError, ValidationError as APIValidationError
from app.api.schemas.support import SupportMessageCreate, SupportTicketCreate
from app.config import settings
from app.database.models.support import SupportMessage, SupportTicket
from app.database.models.user import RoleEnum, User
from app.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)
router = APIRouter(tags=["support"])

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


async def send_new_ticket_alert_bg(ticket_id: int, username: str, telegram_id: int, subject: str, message_text: str, order_id: int | None):
    from aiogram import Bot
    from app.services.notification_service import NotificationService
    from app.database.engine import async_session_maker

    order_info = f" (по сделке #{order_id})" if order_id else ""
    text = (
        f"📩 [Тикет #{ticket_id}] Обращение в поддержку от @{username} (ID: {telegram_id}){order_info}:\n"
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

async def send_ticket_reply_alert_bg(is_staff: bool, owner_user_id: int, ticket_id: int, subject: str, text: str, username: str, telegram_id: int):
    from aiogram import Bot
    from app.services.notification_service import NotificationService
    from app.database.engine import async_session_maker

    async with async_session_maker() as session:
        if is_staff:
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
            try:
                async with Bot(token=settings.BOT_TOKEN) as bot:
                    notif_service = NotificationService(session)
                    alert_text = (
                        f"💬 [Тикет #{ticket_id}] Новый ответ от клиента @{username} "
                        f"(ID: {telegram_id}):\n"
                        f"Тема: {subject}\n"
                        f"Сообщение: {text}"
                    )
                    await notif_service.send_to_all_chats(bot, alert_text)
            except Exception as e:
                logger.error(f"Failed to send client ticket reply alert to staff Telegram: {e}")

async def send_ticket_closed_alert_bg(is_staff: bool, owner_user_id: int, ticket_id: int, subject: str, username: str):
    from aiogram import Bot
    from app.services.notification_service import NotificationService
    from app.database.engine import async_session_maker

    async with async_session_maker() as session:
        if is_staff:
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


@router.get("/api/v1/support/tickets")
async def list_support_tickets(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """List support tickets. Clients see only their own; staff see all tickets."""
    if current_user.role in (RoleEnum.operator, RoleEnum.admin, RoleEnum.super_admin):
        # Staff role: see all tickets
        stmt = select(SupportTicket).order_by(SupportTicket.updated_at.desc())
        result = await session.execute(stmt)
        tickets = result.scalars().all()
        return [ticket_to_dict(t) for t in tickets]

    # Client role: see their own tickets
    stmt = (
        select(SupportTicket)
        .where(SupportTicket.user_id == current_user.id)
        .order_by(SupportTicket.updated_at.desc())
    )
    result = await session.execute(stmt)
    tickets = result.scalars().all()
    return [ticket_to_dict(t) for t in tickets]


@router.post("/api/v1/support/tickets", status_code=201)
async def create_support_ticket(
    ticket_data: SupportTicketCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Create a support ticket in PostgreSQL and notify Telegram operators."""
    if not ticket_data.message:
        raise APIValidationError("Message text is required")

    username = current_user.username or "N/A"
    sender_name = current_user.full_name or username or "Клиент"

    ticket = SupportTicket(
        user_id=current_user.id,
        subject=ticket_data.subject,
        order_id=ticket_data.order_id,
        status="open",
    )
    session.add(ticket)
    await session.flush()

    first_msg = SupportMessage(
        ticket_id=ticket.id,
        sender_id=current_user.id,
        sender_name=sender_name,
        sender_role="client",
        text=ticket_data.message,
    )
    session.add(first_msg)
    await session.commit()

    stmt = select(SupportTicket).where(SupportTicket.id == ticket.id)
    result = await session.execute(stmt)
    ticket_loaded = result.scalar_one()

    background_tasks.add_task(
        send_new_ticket_alert_bg,
        ticket_id=ticket_loaded.id,
        username=username,
        telegram_id=current_user.telegram_id,
        subject=ticket_data.subject,
        message_text=ticket_data.message,
        order_id=ticket_data.order_id
    )

    return ticket_to_dict(ticket_loaded)


@router.get("/api/v1/support/tickets/{ticket_id}/messages")
async def get_ticket_messages(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get all messages for a specific support ticket."""
    stmt = select(SupportTicket).where(SupportTicket.id == ticket_id)
    result = await session.execute(stmt)
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise NotFoundError("Support ticket not found")

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

    return messages


@router.post("/api/v1/support/tickets/{ticket_id}/messages", status_code=201)
async def send_ticket_message(
    ticket_id: int,
    msg_data: SupportMessageCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Send a reply inside an active support ticket (handles both client and staff)."""
    text = msg_data.text
    if not text:
        raise APIValidationError("Message text is required")

    username = current_user.username or "N/A"
    sender_name = current_user.full_name or username or (
        "Сотрудник" if current_user.role != RoleEnum.client else "Клиент"
    )

    stmt = select(SupportTicket).where(SupportTicket.id == ticket_id)
    result = await session.execute(stmt)
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise NotFoundError("Support ticket not found")

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

    ticket.status = "open"
    ticket.updated_at = datetime.now(UTC).replace(tzinfo=None)
    await session.commit()

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
    
    is_staff = current_user.role in (RoleEnum.operator, RoleEnum.admin, RoleEnum.super_admin)
    
    background_tasks.add_task(
        send_ticket_reply_alert_bg,
        is_staff=is_staff,
        owner_user_id=ticket.user_id,
        ticket_id=ticket_id,
        subject=ticket.subject,
        text=text,
        username=username,
        telegram_id=current_user.telegram_id
    )

    return response_data


@router.post("/api/v1/support/tickets/{ticket_id}/close")
async def close_ticket(
    ticket_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Close an active support ticket."""
    stmt = select(SupportTicket).where(SupportTicket.id == ticket_id)
    result = await session.execute(stmt)
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise NotFoundError("Support ticket not found")

    if current_user.role == RoleEnum.client and ticket.user_id != current_user.id:
        raise NotFoundError("Support ticket not found")

    ticket.status = "closed"
    ticket.updated_at = datetime.now(UTC).replace(tzinfo=None)
    await session.commit()

    stmt = select(SupportTicket).where(SupportTicket.id == ticket_id)
    result = await session.execute(stmt)
    ticket_loaded = result.scalar_one()
    ticket_dict = ticket_to_dict(ticket_loaded)

    is_staff = current_user.role in (RoleEnum.operator, RoleEnum.admin, RoleEnum.super_admin)

    background_tasks.add_task(
        send_ticket_closed_alert_bg,
        is_staff=is_staff,
        owner_user_id=ticket_loaded.user_id,
        ticket_id=ticket_id,
        subject=ticket_loaded.subject,
        username=current_user.username or "N/A"
    )

    return ticket_dict
