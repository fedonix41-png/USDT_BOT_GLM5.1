"""Telegram WebApp authentication router."""

import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qsl

from aiohttp import web
from pydantic import ValidationError

from app.api.auth import generate_access_token
from app.api.exceptions import UnauthorizedError
from app.api.exceptions import ValidationError as APIValidationError
from app.api.schemas.auth import TelegramVerifyRequest, TokenResponse
from app.config import settings
from app.database.engine import async_session_maker
from app.database.models.user import RoleEnum
from app.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)
router = web.RouteTableDef()


def verify_telegram_webapp_data(init_data: str, bot_token: str) -> dict | None:
    """Verify Telegram WebApp initData signature."""
    try:
        parsed_data = dict(parse_qsl(init_data))
        received_hash = parsed_data.pop('hash', None)
        
        if not received_hash:
            return None
        
        data_check_string = '\n'.join(f'{k}={v}' for k, v in sorted(parsed_data.items()))
        secret_key = hmac.new('WebAppData'.encode(), bot_token.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        if calculated_hash != received_hash:
            return None
        
        user_data = json.loads(parsed_data.get('user', '{}'))
        return user_data
    except Exception as e:
        logger.error(f"Error verifying Telegram data: {e}")
        return None


@router.post("/api/v1/auth/telegram/verify")
async def telegram_verify(request: web.Request) -> web.Response:
    """Verify Telegram WebApp initData and return JWT token."""
    try:
        body_text = request.get("body_text", "")
        if not body_text:
            body_text = await request.text()
        data = json.loads(body_text)
        verify_data = TelegramVerifyRequest(**data)
    except json.JSONDecodeError:
        raise APIValidationError("Invalid JSON body")
    except ValidationError as e:
        raise APIValidationError(str(e))

    user_data = verify_telegram_webapp_data(verify_data.initData, settings.BOT_TOKEN)
    
    if not user_data:
        raise UnauthorizedError("Invalid Telegram data")
    
    telegram_id = user_data.get('id')
    username = user_data.get('username')
    first_name = user_data.get('first_name', '')
    last_name = user_data.get('last_name', '')
    full_name = f"{first_name} {last_name}".strip()
    
    if not telegram_id:
        raise UnauthorizedError("Missing Telegram ID")
    
    async with async_session_maker() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(telegram_id)
        
        if not user:
            user = await user_repo.create(
                telegram_id=telegram_id,
                username=username,
                full_name=full_name,
                role=RoleEnum.client
            )
        
        if user.is_blocked:
            raise UnauthorizedError("User is blocked")
        
        access_token, access_jti, expires_in = generate_access_token(user.id, user.role.value)
        
        response_data = TokenResponse(
            access_token=access_token,
            token=access_token,
            user={
                'id': user.id,
                'telegram_id': user.telegram_id,
                'username': user.username,
                'full_name': user.full_name,
                'role': user.role.value,
                'is_blocked': user.is_blocked,
                'balance': float(user.balance) if hasattr(user, 'balance') else 0.0,
                'fiat_balance': float(user.fiat_balance) if hasattr(user, 'fiat_balance') else 0.0,
                'referrals_count': user.referrals_count if hasattr(user, 'referrals_count') else 0,
                'referral_earned': float(user.referral_earned) if hasattr(user, 'referral_earned') else 0.0,
                'created_at': user.created_at.isoformat()
            },
            expires_in=expires_in
        )
        
        logger.info(f"Telegram user {telegram_id} authenticated")
        
        return web.json_response(response_data.model_dump(mode='json'))
