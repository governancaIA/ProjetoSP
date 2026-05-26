"""
Storage service for MinIO/S3 file management
"""
import hashlib
import tempfile
from io import BytesIO
from typing import AsyncIterator, Tuple
from minio import Minio
from minio.error import S3Error
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# 8 MB chunks — MinIO multipart minimum is 5 MB; 8 MB balances memory vs round-trips
_CHUNK_SIZE = 8 * 1024 * 1024


class StorageServiceError(Exception):
    """Storage service error"""
    pass


class StorageService:
    """
    Abstraction layer for MinIO/S3 storage.
    Handles upload, download, and file management.
    """

    def __init__(self):
        """Initialize MinIO client"""
        try:
            self.client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_USE_SSL,
            )
            self.bucket = settings.MINIO_BUCKET_NAME

            # Ensure bucket exists
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info(f"Created bucket: {self.bucket}")

        except S3Error as e:
            logger.error(f"Failed to initialize MinIO client: {str(e)}")
            raise StorageServiceError(f"MinIO initialization failed: {str(e)}")

    async def upload_stream(
        self,
        file_stream: AsyncIterator[bytes],
        key: str,
        content_type: str = "application/octet-stream",
        max_size: int = 2 * 1024 * 1024 * 1024,
    ) -> Tuple[str, str, int]:
        """
        Stream-upload a file to MinIO without loading it fully in RAM.

        Reads the async iterator in 8 MB chunks, computing SHA-256 and total
        size incrementally, then uploads via MinIO put_object using a
        synchronous BytesIO pipe filled from a collected buffer.

        Args:
            file_stream: Async iterator yielding bytes (from UploadFile.stream())
            key: Storage key
            content_type: MIME type
            max_size: Hard limit in bytes — raises StorageServiceError if exceeded

        Returns:
            (key, sha256_hex, total_bytes)

        Raises:
            StorageServiceError: If file exceeds max_size or upload fails
        """
        hasher = hashlib.sha256()
        total_bytes = 0

        # Spill to disk after 50 MB — avoids OOM on large SPED files while
        # keeping small files fast (in-memory spool)
        _SPOOL_THRESHOLD = 50 * 1024 * 1024

        try:
            with tempfile.SpooledTemporaryFile(max_size=_SPOOL_THRESHOLD) as spool:
                async for chunk in file_stream:
                    total_bytes += len(chunk)
                    if total_bytes > max_size:
                        raise StorageServiceError(
                            f"File exceeds maximum size of {max_size} bytes"
                        )
                    hasher.update(chunk)
                    spool.write(chunk)

                file_hash = hasher.hexdigest()
                spool.seek(0)

                self.client.put_object(
                    self.bucket,
                    key,
                    spool,
                    length=total_bytes,
                    content_type=content_type,
                )

            logger.info(f"Streamed upload {key} ({total_bytes} bytes) to {self.bucket}")
            return key, file_hash, total_bytes

        except StorageServiceError:
            raise
        except S3Error as e:
            logger.error(f"Failed to upload {key}: {str(e)}")
            raise StorageServiceError(f"Upload failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error uploading {key}: {str(e)}")
            raise StorageServiceError(f"Unexpected error during upload: {str(e)}")

    def upload(
        self,
        content: bytes,
        key: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Upload file bytes to MinIO (synchronous, for small/known-size content).

        For files larger than a few MB, prefer upload_stream() to avoid
        loading the entire file in RAM.
        """
        try:
            file_obj = BytesIO(content)
            self.client.put_object(
                self.bucket,
                key,
                file_obj,
                length=len(content),
                content_type=content_type,
            )
            logger.info(f"Uploaded {key} to {self.bucket}")
            return key

        except S3Error as e:
            logger.error(f"Failed to upload {key}: {str(e)}")
            raise StorageServiceError(f"Upload failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error uploading {key}: {str(e)}")
            raise StorageServiceError(f"Unexpected error during upload: {str(e)}")

    def download(self, key: str) -> bytes:
        """
        Download file from MinIO.

        Args:
            key: Storage key

        Returns:
            File content (bytes)

        Raises:
            StorageServiceError: If download fails or key not found
        """
        try:
            response = self.client.get_object(self.bucket, key)
            content = response.read()
            response.close()

            logger.info(f"Downloaded {key} from {self.bucket}")
            return content

        except S3Error as e:
            if e.code == "NoSuchKey":
                logger.warning(f"Key not found: {key}")
                raise StorageServiceError(f"File not found: {key}")
            logger.error(f"Failed to download {key}: {str(e)}")
            raise StorageServiceError(f"Download failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error downloading {key}: {str(e)}")
            raise StorageServiceError(f"Unexpected error during download: {str(e)}")

    def delete(self, key: str) -> None:
        """
        Delete file from MinIO.

        Args:
            key: Storage key

        Raises:
            StorageServiceError: If deletion fails
        """
        try:
            self.client.remove_object(self.bucket, key)
            logger.info(f"Deleted {key} from {self.bucket}")

        except S3Error as e:
            if e.code == "NoSuchKey":
                logger.warning(f"Key not found during deletion: {key}")
                return
            logger.error(f"Failed to delete {key}: {str(e)}")
            raise StorageServiceError(f"Deletion failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error deleting {key}: {str(e)}")
            raise StorageServiceError(f"Unexpected error during deletion: {str(e)}")

    def exists(self, key: str) -> bool:
        """
        Check if key exists in MinIO.

        Args:
            key: Storage key

        Returns:
            True if exists, False otherwise
        """
        try:
            self.client.stat_object(self.bucket, key)
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            logger.error(f"Error checking key {key}: {str(e)}")
            return False

    @staticmethod
    def build_storage_key(tenant_id: str, document_type: str, file_hash: str, ext: str = "txt") -> str:
        """
        Build storage key from components.

        Args:
            tenant_id: Organization/tenant ID
            document_type: Document type (sped_efd_icms, nfe, cte, etc)
            file_hash: SHA-256 hash of file
            ext: File extension (default: txt)

        Returns:
            Storage key (e.g., org_001/sped_efd_icms/abc123def456.txt)
        """
        return f"{tenant_id}/{document_type}/{file_hash}.{ext}"

    @staticmethod
    def calculate_file_hash(content: bytes) -> str:
        """
        Calculate SHA-256 hash of file content.

        Args:
            content: File bytes

        Returns:
            Hex string of SHA-256 hash
        """
        return hashlib.sha256(content).hexdigest()

    def get_tenant_storage_usage(self, tenant_id: str) -> int:
        """
        Calculate total storage usage for a tenant by listing objects.

        Args:
            tenant_id: Tenant ID

        Returns:
            Total size in bytes of all objects for tenant

        Note:
            This is expensive for large tenants. Prefer database-backed
            calculation in document_service._get_tenant_storage_usage()
        """
        try:
            total_size = 0
            prefix = f"{tenant_id}/"

            # List all objects with tenant prefix
            objects = self.client.list_objects(self.bucket, prefix=prefix)
            for obj in objects:
                total_size += obj.size

            logger.info(f"Tenant {tenant_id} storage usage: {total_size} bytes")
            return total_size

        except S3Error as e:
            logger.error(f"Error calculating storage usage for {tenant_id}: {str(e)}")
            return 0
