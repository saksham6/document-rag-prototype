from abc import ABC, abstractmethod
from fastapi import UploadFile


from document_rag_prototype.core.config import UPLOAD_FOLDER


class StorageService(ABC):
    @abstractmethod
    async def save_file(self, file: UploadFile, filename: str) -> str:
        pass


class LocalStorageService(StorageService):
    async def save_file(self, file: UploadFile, filename: str) -> str:
        UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

        file_path = UPLOAD_FOLDER / filename

        content = await file.read()

        with open(file_path, "wb") as buffer:
            buffer.write(content)

        return str(file_path)


storage_service = LocalStorageService()