from typing import AsyncIterator, Tuple

from azure.storage.blob.aio import BlobServiceClient
from fastapi import UploadFile, HTTPException

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

    async def delete_file(self, filename: str, container_name: str) -> bool:
        try:
            async with BlobServiceClient.from_connection_string(self.connection_string) as blob_service_client:
                container_client = blob_service_client.get_container_client(container_name)
                blob_client = container_client.get_blob_client(filename)

                # Check if blob exists before deleting
                exists = await blob_client.exists()
                if not exists:
                    return False

                # Delete the blob
                await blob_client.delete_blob()
                return True
        except Exception:
            return False

    async def download_file(self, filename: str, container_name: str) -> Tuple[AsyncIterator[bytes], int]:
        """Download file from blob storage and return content stream and size"""
        try:
            async with BlobServiceClient.from_connection_string(self.connection_string) as blob_service_client:
                container_client = blob_service_client.get_container_client(container_name)
                blob_client = container_client.get_blob_client(filename)

                # Check if blob exists
                exists = await blob_client.exists()
                if not exists:
                    raise HTTPException(status_code=404, detail=f"File {filename} not found")

                # Get blob properties to get the size
                properties = await blob_client.get_blob_properties()
                size = properties.size

                # Download the blob
                download_stream = await blob_client.download_blob()
                return download_stream.chunks(), size

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")
