"""Rates router for API."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session, require_min_role
from app.api.exceptions import ValidationError as APIValidationError
from app.api.schemas.rate import CurrentRatesResponse, RateCreateRequest, RateHistoryResponse, RateResponse
from app.database.models.rate import RateTypeEnum
from app.database.models.user import RoleEnum, User
from app.services.rate_service import RateService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["rates"])


@router.get("/api/v1/rates", response_model=CurrentRatesResponse)
async def get_current_rates(session: AsyncSession = Depends(get_session)):
    rate_service = RateService(session)
    buy_rate = await rate_service.get_current_rate(RateTypeEnum.buy)
    sell_rate = await rate_service.get_current_rate(RateTypeEnum.sell)

    return CurrentRatesResponse(
        buy=buy_rate,
        sell=sell_rate,
    )


@router.get("/api/v1/rates/history", response_model=RateHistoryResponse)
async def get_rate_history(
    type: str = Query("buy"),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(require_min_role(RoleEnum.operator)),
    session: AsyncSession = Depends(get_session)
):
    try:
        rate_type = RateTypeEnum(type)
    except ValueError:
        raise APIValidationError(f"Invalid rate type: {type}")

    rate_service = RateService(session)
    history = await rate_service.get_rate_history(rate_type, limit)

    return RateHistoryResponse(
        items=[RateResponse.model_validate(r) for r in history],
        total=len(history),
    )


@router.post("/api/v1/rates", response_model=RateResponse, status_code=201)
async def set_rate(
    rate_data: RateCreateRequest,
    current_user: User = Depends(require_min_role(RoleEnum.admin)),
    session: AsyncSession = Depends(get_session)
):
    rate_service = RateService(session)
    rate = await rate_service.set_rate(rate_data.rate_type, rate_data.value, current_user.id)

    logger.info(f"User {current_user.telegram_id} set {rate_data.rate_type.value} rate to {rate_data.value}")

    return RateResponse.model_validate(rate)
