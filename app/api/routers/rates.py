"""Rates router for API."""

import json
import logging

from aiohttp import web
from pydantic import ValidationError

from app.api.deps import get_current_user, require_min_role
from app.api.exceptions import ValidationError as APIValidationError
from app.api.schemas.rate import CurrentRatesResponse, RateCreateRequest, RateHistoryResponse, RateResponse
from app.database.engine import async_session_maker
from app.database.models.rate import RateTypeEnum
from app.database.models.user import RoleEnum
from app.services.rate_service import RateService

logger = logging.getLogger(__name__)
router = web.RouteTableDef()


@router.get("/api/v1/rates")
async def get_current_rates(request: web.Request) -> web.Response:
    async with async_session_maker() as session:
        rate_service = RateService(session)
        buy_rate = await rate_service.get_current_rate(RateTypeEnum.buy)
        sell_rate = await rate_service.get_current_rate(RateTypeEnum.sell)

        response = CurrentRatesResponse(
            buy=buy_rate,
            sell=sell_rate,
        )

        return web.json_response(response.model_dump(mode='json'))


@router.get("/api/v1/rates/history")
async def get_rate_history(request: web.Request) -> web.Response:
    await require_min_role(RoleEnum.operator)(request)

    rate_type_str = request.query.get("type", "buy")
    limit = int(request.query.get("limit", "10"))
    limit = min(limit, 50)

    try:
        rate_type = RateTypeEnum(rate_type_str)
    except ValueError:
        raise APIValidationError(f"Invalid rate type: {rate_type_str}")

    async with async_session_maker() as session:
        rate_service = RateService(session)
        history = await rate_service.get_rate_history(rate_type, limit)

        response = RateHistoryResponse(
            items=[RateResponse.model_validate(r) for r in history],
            total=len(history),
        )

        return web.json_response(response.model_dump(mode='json'))


@router.post("/api/v1/rates")
async def set_rate(request: web.Request) -> web.Response:
    current_user = await get_current_user(request)
    await require_min_role(RoleEnum.admin)(request)

    try:
        body_text = request.get("body_text", "")
        if not body_text:
            body_text = await request.text()
        data = json.loads(body_text)
        rate_data = RateCreateRequest(**data)
    except json.JSONDecodeError:
        raise APIValidationError("Invalid JSON body")
    except ValidationError as e:
        raise APIValidationError(str(e))

    async with async_session_maker() as session:
        rate_service = RateService(session)
        rate = await rate_service.set_rate(rate_data.rate_type, rate_data.value, current_user.id)

        logger.info(f"User {current_user.telegram_id} set {rate_data.rate_type.value} rate to {rate_data.value}")

        return web.json_response(RateResponse.model_validate(rate).model_dump(mode='json'), status=201)
