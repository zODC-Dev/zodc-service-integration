from datetime import datetime, timezone
from typing import Optional

from sqlmodel import and_, col, select, update
from sqlmodel.ext.asyncio.session import AsyncSession

from src.configs.logger import log
from src.domain.constants.refresh_tokens import TokenType
from src.domain.models.refresh_token import RefreshTokenModel
from src.domain.repositories.refresh_token_repository import IRefreshTokenRepository
from src.infrastructure.entities.refresh_token import RefreshTokenEntity


class SQLAlchemyRefreshTokenRepository(IRefreshTokenRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_refresh_token(self, refresh_token: RefreshTokenModel) -> RefreshTokenModel:
        """Create new refresh token and revoke old ones"""
        try:
            # Convert to UTC then remove timezone info for database
            expires_at_utc = refresh_token.expires_at.astimezone(timezone.utc).replace(tzinfo=None)
            created_at_utc = datetime.now(timezone.utc).replace(tzinfo=None)

            # Revoke all existing non-revoked tokens for this user and type
            revoke_stmt = (
                update(RefreshTokenEntity)
                .where(
                    and_(
                        RefreshTokenEntity.user_id == refresh_token.user_id,
                        RefreshTokenEntity.token_type == refresh_token.token_type,
                        RefreshTokenEntity.is_revoked == False  # noqa: E712
                    )
                )
                .values(is_revoked=True)
            )
            await self.session.exec(revoke_stmt)  # type: ignore

            # Create new token
            db_token = RefreshTokenEntity(
                token=refresh_token.token,
                user_id=refresh_token.user_id,
                expires_at=expires_at_utc,
                is_revoked=refresh_token.is_revoked,
                token_type=refresh_token.token_type,
                created_at=created_at_utc
            )
            self.session.add(db_token)

            # Commit changes
            await self.session.commit()
            await self.session.refresh(db_token)

            return self._to_domain(db_token)

        except Exception as e:
            await self.session.rollback()
            log.error(f"Error creating refresh token: {str(e)}")
            raise

    async def get_by_token(self, token: str) -> Optional[RefreshTokenModel]:
        result = await self.session.exec(
            select(RefreshTokenEntity).where(RefreshTokenEntity.token == token)
        )
        db_token = result.first()
        return self._to_domain(db_token) if db_token else None

    async def revoke_token(self, token: str) -> None:
        result = await self.session.exec(
            select(RefreshTokenEntity).where(RefreshTokenEntity.token == token)
        )
        db_token = result.first()
        if db_token:
            db_token.is_revoked = True
            await self.session.commit()

    async def get_by_user_id_and_type(self, user_id: int, token_type: TokenType) -> Optional[RefreshTokenModel]:
        """Get refresh token by user id and token type by last created"""
        result = await self.session.exec(
            select(RefreshTokenEntity).where(
                and_(
                    RefreshTokenEntity.user_id == user_id,
                    RefreshTokenEntity.token_type == token_type
                )
            ).order_by(col(RefreshTokenEntity.created_at).desc())
        )
        db_token = result.first()
        return self._to_domain(db_token) if db_token else None

    async def revoke_tokens_by_user_and_type(self, user_id: int, token_type: TokenType) -> None:
        """Revoke all tokens of a specific type for a user"""
        stmt = (
            update(RefreshTokenEntity)
            .where(
                and_(
                    RefreshTokenEntity.user_id == user_id,
                    RefreshTokenEntity.token_type == token_type,
                    RefreshTokenEntity.is_revoked == False  # noqa: E712
                )
            )
            .values(is_revoked=True)
        )
        await self.session.exec(stmt)  # type: ignore
        await self.session.commit()

    async def cleanup_expired_tokens(self) -> None:
        """Clean up expired tokens by marking them as revoked"""
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)  # Convert to naive UTC
        stmt = (
            update(RefreshTokenEntity)
            .where(
                and_(
                    RefreshTokenEntity.expires_at < now_utc,
                    RefreshTokenEntity.is_revoked == False  # noqa: E712
                )
            )
            .values(is_revoked=True)
        )
        await self.session.exec(stmt)  # type: ignore
        await self.session.commit()

    def _to_domain(self, db_token: RefreshTokenEntity) -> RefreshTokenModel:
        # Add UTC timezone info when converting back to domain entity
        return RefreshTokenModel(
            token=db_token.token,
            user_id=db_token.user_id,
            expires_at=datetime.combine(
                db_token.expires_at.date(),
                db_token.expires_at.time(),
                timezone.utc
            ),
            is_revoked=db_token.is_revoked,
            created_at=datetime.combine(
                db_token.created_at.date(),
                db_token.created_at.time(),
                timezone.utc
            ),
            token_type=db_token.token_type
        )
