from azure.storage.blob.aio import BlobServiceClient
from fastapi import UploadFile

from src.configs.settings import settings
from src.domain.services.blob_storage_service import IBlobStorageService


class AzureBlobStorageService(IBlobStorageService):
    def __init__(self) -> None:
        self.connection_string = settings.AZURE_STORAGE_CONNECTION_STRING
        self.account_url = f"https://{
            settings.AZURE_STORAGE_ACCOUNT}.blob.core.windows.net"

    async def upload_file(self, file: UploadFile, container_name: str) -> str:
        async with BlobServiceClient.from_connection_string(self.connection_string) as blob_service_client:
            container_client = blob_service_client.get_container_client(
                container_name)

            # Create blob client
            blob_client = container_client.get_blob_client(file.filename)

            # Upload file
            contents = await file.read()
            await blob_client.upload_blob(contents, overwrite=True)

            # Return blob URL
            return f"{self.account_url}/{container_name}/{file.filename}"
