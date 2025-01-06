from fastapi import HTTPException, UploadFile

from src.app.services.util_service import UtilService


class UtilController:
    def __init__(self, util_service: UtilService):
        self.util_service = util_service

    async def extract_excel(self, file: UploadFile):
        try:
            result = await self.util_service.extract_excel(file)
            return result
        except Exception as e:
            # raise XXX from e to avoid Ruff check error
            raise HTTPException(
                500, detail=f"Error processing file: {e}") from e

    async def upload_excel_to_blob(self, file: UploadFile) -> str:
        try:
            blob_url = await self.util_service.upload_excel_to_blob(file)
            return blob_url
        except Exception as e:
            raise HTTPException(
                500,
                detail=f"Failed to upload file: {str(e)}"
            ) from e
