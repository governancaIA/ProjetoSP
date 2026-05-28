"""
Storage service for MinIO/S3 file management
"""
import hashlib
import os
import tempfile
from io import BytesIO
from typing import AsyncIterator, Optional, Tuple
from minio import Minio
from minio.error import S3Error
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# 8 MB chunks — MinIO multipart minimum is 5 MB; 8 MB balances memory vs round-trips
_CHUNK_SIZE = 8 * 1024 * 1024

# Multipart threshold: files >100 MB use MinIO's native multipart via part_size=
# 50 MB parts × 4 Celery workers = 200 MB max simultaneous buffer (fits in 2 GB worker RAM)
_MULTIPART_THRESHOLD = 100 * 1024 * 1024
_PART_SIZE = 50 * 1024 * 1024


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

        Writes incoming chunks to a temporary file on disk (peak RAM: one chunk = 8 MB
        per concurrent upload regardless of file size), then uploads from disk to MinIO.
        The temp file is always cleaned up, even on error.

        Args:
            file_stream: Async iterator yielding bytes
            key: Storage key (must be the permanent key — no rename after)
            content_type: MIME type
            max_size: Hard limit in bytes — raises StorageServiceError if exceeded

        Returns:
            (key, sha256_hex, total_bytes)

        Raises:
            StorageServiceError: If file exceeds max_size or upload fails
        """
        hasher = hashlib.sha256()
        total_bytes = 0
        tmp_path: Optional[str] = None

        try:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_path = tmp.name
                async for chunk in file_stream:
                    total_bytes += len(chunk)
                    if total_bytes > max_size:
                        raise StorageServiceError(
                            f"File exceeds maximum size of {max_size} bytes"
                        )
                    hasher.update(chunk)
                    tmp.write(chunk)

            file_hash = hasher.hexdigest()
            use_multipart = total_bytes > _MULTIPART_THRESHOLD

            with open(tmp_path, "rb") as f:
                self.client.put_object(
                    self.bucket,
                    key,
                    f,
                    length=total_bytes,
                    content_type=content_type,
                    part_size=_PART_SIZE if use_multipart else 0,
                )

            logger.info(
                f"Streamed upload {key} ({total_bytes} bytes, "
                f"multipart={use_multipart}) to {self.bucket}"
            )
            return key, file_hash, total_bytes

        except StorageServiceError:
            raise
        except S3Error as e:
            logger.error(f"Failed to upload {key}: {str(e)}")
            raise StorageServiceError(f"Upload failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error uploading {key}: {str(e)}")
            raise StorageServiceError(f"Unexpected error during upload: {str(e)}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    logger.warning(f"Failed to clean up temp file: {tmp_path}")

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
