from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile

from src.app.schemas.responses.base import StandardResponse
from src.app.schemas.responses.media import MediaResponse
from src.app.controllers.media_controller import MediaController
from src.app.dependencies.auth import get_jwt_claims
from src.app.dependencies.media import get_media_controller
from src.app.schemas.requests.auth import JWTClaims

router = APIRouter()


@router.post("/upload", response_model=StandardResponse[MediaResponse])
async def upload_media(
    file: Annotated[UploadFile, File(...)],
    controller: MediaController = Depends(get_media_controller),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """Upload media file and return media info"""
    user_id = int(claims.sub)
    return await controller.upload_media(file, user_id)


@router.get("/{media_id}")
async def get_media(
    media_id: UUID,
    controller: MediaController = Depends(get_media_controller),
):
    """Get media file by id"""
    return await controller.get_media(media_id)
