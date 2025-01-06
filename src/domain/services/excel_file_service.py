from abc import ABC, abstractmethod
from typing import Any, Dict

from fastapi import UploadFile


class IExcelFileService(ABC):
    @abstractmethod
    async def extract_file(self, file: UploadFile) -> Dict[str, Any]:
        """Extract excel data in form create"""
        pass
