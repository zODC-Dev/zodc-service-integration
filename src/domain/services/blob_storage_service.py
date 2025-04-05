from abc import ABC, abstractmethod

from fastapi import UploadFile


class IBlobStorageService(ABC):
    @abstractmethod
    async def upload_file(self, file: UploadFile, container_name: str) -> str:
        """Upload file to blob storage and return the URL"""
        pass

    @abstractmethod
    async def delete_file(self, filename: str, container_name: str) -> bool:
        """Delete file from blob storage"""
        pass
