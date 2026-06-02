import pytest
from decimal import Decimal

from app.database.models.order import OrderTypeEnum
from app.services.settings_service import SettingsService
from app.repositories.settings_repo import SettingsRepository
from app.database.models import GlobalSettings, AuditLog
from sqlalchemy import select


@pytest.mark.asyncio
async def test_requisites_encryption(session, encryption_service, admin_user):
    """
    Проверяем что реквизиты шифруются в БД и маскируются в audit_logs.
    """
    svc = SettingsService(session, encryption_service)
    
    # 1. Устанавливаем реквизиты карты
    card_number = "4276 1234 5678 9012"
    await svc.set_requisites_card(card_number, user_id=admin_user.id)
    await session.commit()
    
    # 2. Проверяем что в global_settings значение ЗАШИФРОВАНО
    result = await session.get(GlobalSettings, "requisites_card")
    assert result is not None
    assert result.value != card_number, "Значение должно быть зашифровано!"
    # Мы используем Fernet (cryptography), поэтому обычно префикс начинается с 'gAAAAA'
    assert result.value != "", "Значение не должно быть пустым"
    
    # 3. Проверяем что decrypt возвращает оригинал
    decrypted = await svc.get_requisites_card()
    assert decrypted == card_number
    
    # 4. Проверяем audit_logs — там должно быть "***"
    stmt = select(AuditLog).where(AuditLog.action == "change_setting_requisites_card")
    audit_log = (await session.execute(stmt)).scalar_one_or_none()
    assert audit_log is not None
    assert audit_log.details["value"] == "***", "В audit_logs должно быть маскированное значение"
