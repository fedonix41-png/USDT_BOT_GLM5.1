"""Audit service — log actions."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.audit_log import AuditLog
from app.repositories.audit_repo import AuditRepository


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit_repo = AuditRepository(session)

    async def log(self, user_id: int, action: str, details: dict | None = None) -> AuditLog:
        return await self.audit_repo.log(user_id=user_id, action=action, details=details)
