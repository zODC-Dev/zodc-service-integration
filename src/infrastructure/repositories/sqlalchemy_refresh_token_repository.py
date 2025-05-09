from datetime import datetime, timezone
from typing import Optional

from sqlmodel import and_, col, select, update
from sqlmodel.ext.asyncio.session import AsyncSession

from src.configs.logger import log
from src.domain.constants.refresh_tokens import TokenType
from src.domain.models.database.refresh_token import RefreshTokenDBCreateDTO
from src.domain.models.refresh_token import RefreshTokenModel
from src.domain.repositories.refresh_token_repository import IRefreshTokenRepository
from src.infrastructure.entities.refresh_token import RefreshTokenEntity


class SQLAlchemyRefreshTokenRepository(IRefreshTokenRepository):
    def __init__(self):
        pass

    async def create_refresh_token(self, session: AsyncSession, refresh_token_dto: RefreshTokenDBCreateDTO) -> RefreshTokenModel:
        """Create new refresh token and revoke old ones"""
        try:
            # Convert to UTC then remove timezone info for database
            expires_at_utc = refresh_token_dto.expires_at.astimezone(timezone.utc).replace(tzinfo=None)
            created_at_utc = datetime.now(timezone.utc).replace(tzinfo=None)

            # Revoke all existing non-revoked tokens for this user and type
            revoke_stmt = (
                update(RefreshTokenEntity)
                .where(
                    and_(
                        col(RefreshTokenEntity.user_id) == refresh_token_dto.user_id,
                        col(RefreshTokenEntity.token_type) == refresh_token_dto.token_type,
                        col(RefreshTokenEntity.is_revoked) == False  # noqa: E712
                    )
                )
                .values(is_revoked=True)
            )
            await session.exec(revoke_stmt)  # type: ignore

            # Create new token
            db_token = RefreshTokenEntity(
                token=refresh_token_dto.token,
                user_id=refresh_token_dto.user_id,
                token_type=refresh_token_dto.token_type,
                expires_at=expires_at_utc,
                created_at=created_at_utc
            )
            session.add(db_token)

            # Let the session manager handle the transaction
            await session.flush()
            await session.refresh(db_token)

            return self._to_domain(db_token)

        except Exception as e:
            await session.rollback()
            log.error(f"Error creating refresh token: {str(e)}")
            raise

    async def get_by_token(self, session: AsyncSession, token: str) -> Optional[RefreshTokenModel]:
        result = await session.exec(
            select(RefreshTokenEntity).where(col(RefreshTokenEntity.token) == token)
        )
        db_token = result.first()
        return self._to_domain(db_token) if db_token else None

    async def revoke_token(self, session: AsyncSession, token: str) -> None:
        result = await session.exec(
            select(RefreshTokenEntity).where(col(RefreshTokenEntity.token) == token)
        )
        db_token = result.first()
        if db_token:
            db_token.is_revoked = True
            # Let the session manager handle the transaction
            await session.flush()

    async def get_by_user_id_and_type(self, session: AsyncSession, user_id: int, token_type: TokenType) -> Optional[RefreshTokenModel]:
        """Get refresh token by user id and token type by last created"""
        result = await session.exec(
            select(RefreshTokenEntity).where(
                and_(
                    col(RefreshTokenEntity.user_id) == user_id,
                    col(RefreshTokenEntity.token_type) == token_type
                )
            ).order_by(col(RefreshTokenEntity.created_at).desc())
        )
        db_token = result.first()
        return self._to_domain(db_token) if db_token else None

    async def revoke_tokens_by_user_and_type(self, session: AsyncSession, user_id: int, token_type: TokenType) -> None:
        """Revoke all tokens of a specific type for a user"""
        stmt = (
            update(RefreshTokenEntity)
            .where(
                and_(
                    col(RefreshTokenEntity.user_id) == user_id,
                    col(RefreshTokenEntity.token_type) == token_type,
                    col(RefreshTokenEntity.is_revoked) == False  # noqa: E712
                )
            )
            .values(is_revoked=True)
        )
        await session.exec(stmt)  # type: ignore
        # Let the session manager handle the transaction
        await session.flush()

    async def cleanup_expired_tokens(self, session: AsyncSession) -> None:
        """Clean up expired tokens by marking them as revoked"""
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)  # Convert to naive UTC
        stmt = (
            update(RefreshTokenEntity)
            .where(
                and_(
                    col(RefreshTokenEntity.expires_at) < now_utc,
                    col(RefreshTokenEntity.is_revoked) == False  # noqa: E712
                )
            )
            .values(is_revoked=True)
        )
        await session.exec(stmt)  # type: ignore
        # Let the session manager handle the transaction
        await session.flush()

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
