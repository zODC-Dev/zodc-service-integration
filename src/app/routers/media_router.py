from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from sqlmodel.ext.asyncio.session import AsyncSession

from src.app.controllers.media_controller import MediaController
from src.app.dependencies.auth import get_jwt_claims
from src.app.dependencies.controllers import get_media_controller
from src.app.schemas.requests.auth import JWTClaims
from src.app.schemas.responses.base import StandardResponse
from src.app.schemas.responses.media import MediaResponse
from src.configs.database import get_db

router = APIRouter()


@router.post("/upload", response_model=StandardResponse[MediaResponse])
async def upload_media(
    file: Annotated[UploadFile, File(...)],
    controller: MediaController = Depends(get_media_controller),
    claims: JWTClaims = Depends(get_jwt_claims),
    session: AsyncSession = Depends(get_db),
):
    """Upload media file and return media info"""
    user_id = int(claims.sub)
    return await controller.upload_media(session=session, file=file, user_id=user_id)


@router.get("/{media_id}")
async def get_media(
    media_id: UUID,
    controller: MediaController = Depends(get_media_controller),
    session: AsyncSession = Depends(get_db),
):
    """Get media file by id"""
    return await controller.get_media(session=session, media_id=media_id)


@router.delete("/{media_id}", response_model=StandardResponse)
async def remove_media(
    media_id: UUID,
    controller: MediaController = Depends(get_media_controller),
    session: AsyncSession = Depends(get_db),
):
    """Remove media file by id (soft delete)"""
    return await controller.remove_media(session=session, media_id=media_id)
