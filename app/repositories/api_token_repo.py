"""API Token repository for refresh token management."""

from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.api_token import APIToken
from app.repositories.base import BaseRepository


class APITokenRepository(BaseRepository[APIToken]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(APIToken, session)

    async def get_by_jti(self, jti: str) -> APIToken | None:
        stmt = select(APIToken).where(APIToken.jti == jti, APIToken.revoked.is_(False))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_by_user(self, user_id: int) -> list[APIToken]:
        stmt = (
            select(APIToken)
            .where(APIToken.user_id == user_id, APIToken.revoked.is_(False), APIToken.expires_at > datetime.utcnow())
            .order_by(APIToken.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def revoke(self, jti: str) -> bool:
        token = await self.get_by_jti(jti)
        if token is None:
            return False
        token.revoked = True
        await self.session.flush()
        return True

    async def revoke_all_for_user(self, user_id: int) -> int:
        stmt = (
            delete(APIToken)
            .where(APIToken.user_id == user_id, APIToken.revoked.is_(False))
            .returning(APIToken.id)
        )
        result = await self.session.execute(stmt)
        return len(result.all())

    async def cleanup_expired(self) -> int:
        stmt = delete(APIToken).where(APIToken.expires_at < datetime.utcnow()).returning(APIToken.id)
        result = await self.session.execute(stmt)
        return len(result.all())

    async def create_token(self, user_id: int, token_hash: str, jti: str, expires_at: datetime) -> APIToken:
        return await self.create(
            user_id=user_id,
            token_hash=token_hash,
            jti=jti,
            expires_at=expires_at,
        )
