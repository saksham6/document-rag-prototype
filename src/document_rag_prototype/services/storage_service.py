import os
from abc import ABC, abstractmethod

from azure.storage.blob.aio import BlobServiceClient
from fastapi import UploadFile

from document_rag_prototype.core.config import UPLOAD_FOLDER


class StorageService(ABC):
    @abstractmethod
    async def save_file(self, file: UploadFile, filename: str) -> str:
        pass

    @abstractmethod
    async def read_file(self, filename: str) -> bytes:
        pass


class LocalStorageService(StorageService):
    async def save_file(self, file: UploadFile, filename: str) -> str:
        UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

        file_path = UPLOAD_FOLDER / filename
        content = await file.read()

        with open(file_path, "wb") as buffer:
            buffer.write(content)

        return str(file_path)

    async def read_file(self, filename: str) -> bytes:
        file_path = UPLOAD_FOLDER / filename

        with open(file_path, "rb") as file:
            return file.read()


class AzureBlobStorageService(StorageService):
    def __init__(self) -> None:
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

        if not connection_string:
            raise RuntimeError(
                "AZURE_STORAGE_CONNECTION_STRING environment variable is not set"
            )

        self.container_name = os.getenv(
            "AZURE_STORAGE_CONTAINER_NAME",
            "uploads",
        )

        self.blob_service_client = BlobServiceClient.from_connection_string(
            connection_string
        )

    async def save_file(self, file: UploadFile, filename: str) -> str:
        container_client = self.blob_service_client.get_container_client(
            self.container_name
        )

        blob_client = container_client.get_blob_client(filename)

        content = await file.read()

        await blob_client.upload_blob(
            content,
            overwrite=True,
        )

        return blob_client.url

    async def read_file(self, filename: str) -> bytes:
        container_client = self.blob_service_client.get_container_client(
            self.container_name
        )

        blob_client = container_client.get_blob_client(filename)

        stream = await blob_client.download_blob()

        return await stream.readall()


storage_backend = os.getenv("STORAGE_BACKEND", "local").lower()

if storage_backend == "azure":
    storage_service = AzureBlobStorageService()
else:
    storage_service = LocalStorageService()


    