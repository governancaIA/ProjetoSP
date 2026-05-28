"""
Tests for StorageService (MinIO abstraction)
"""
import hashlib
import pytest
from unittest.mock import MagicMock, patch
from io import BytesIO

from app.services.storage_service import StorageService, StorageServiceError


@pytest.fixture
def storage_service():
    """Create StorageService with mocked Minio client"""
    with patch('app.services.storage_service.Minio'):
        service = StorageService()
        service.client = MagicMock()
        service.bucket = "test-bucket"
        return service


def test_storage_service_initialization():
    """Test StorageService can be instantiated"""
    with patch('app.services.storage_service.Minio'):
        service = StorageService()
        assert service.bucket is not None


def test_build_storage_key():
    """Test storage key generation"""
    key = StorageService.build_storage_key(
        tenant_id="org_001",
        document_type="sped_efd_icms",
        file_hash="abc123def456",
        ext="txt"
    )
    assert key == "org_001/sped_efd_icms/abc123def456.txt"


def test_build_storage_key_with_xml():
    """Test storage key generation for XML"""
    key = StorageService.build_storage_key(
        tenant_id="org_002",
        document_type="nfe",
        file_hash="xyz789uvw012",
        ext="xml"
    )
    assert key == "org_002/nfe/xyz789uvw012.xml"


def test_calculate_file_hash():
    """Test file hash calculation"""
    content = b"test file content"
    hash_value = StorageService.calculate_file_hash(content)

    # Verify it's a valid SHA256 hash (64 hex chars)
    assert len(hash_value) == 64
    assert all(c in '0123456789abcdef' for c in hash_value)


def test_upload_success(storage_service):
    """Test successful file upload"""
    content = b"test content"
    key = "org_001/sped_efd_icms/abc123.txt"

    storage_service.client.put_object.return_value = None

    result = storage_service.upload(content, key, "text/plain")

    assert result == key
    storage_service.client.put_object.assert_called_once()


def test_upload_failure(storage_service):
    """Test upload failure raises StorageServiceError"""
    storage_service.client.put_object.side_effect = Exception("Access denied")

    with pytest.raises(StorageServiceError):
        storage_service.upload(b"content", "key", "text/plain")


def test_download_success(storage_service):
    """Test successful file download"""
    key = "org_001/sped_efd_icms/abc123.txt"
    expected_content = b"downloaded content"

    mock_response = MagicMock()
    mock_response.read.return_value = expected_content
    storage_service.client.get_object.return_value = mock_response

    result = storage_service.download(key)

    assert result == expected_content
    storage_service.client.get_object.assert_called_once_with(storage_service.bucket, key)
    mock_response.close.assert_called_once()


def test_download_not_found(storage_service):
    """Test download with non-existent key"""
    from minio.error import S3Error as MinioS3Error

    # Create a mock S3Error with code attribute
    error = MagicMock(spec=MinioS3Error)
    error.code = "NoSuchKey"
    storage_service.client.get_object.side_effect = error

    with pytest.raises(StorageServiceError):
        storage_service.download("nonexistent/key")


def test_delete_success(storage_service):
    """Test successful file deletion"""
    key = "org_001/sped_efd_icms/abc123.txt"
    storage_service.client.remove_object.return_value = None

    storage_service.delete(key)

    storage_service.client.remove_object.assert_called_once_with(storage_service.bucket, key)


def test_delete_not_found(storage_service):
    """Test deletion of non-existent key (should not raise)"""
    from minio.error import S3Error as MinioS3Error

    # S3Error requires a real response object; patch isinstance check instead
    # by raising a real exception subclass that carries .code
    class FakeS3Error(Exception):
        def __init__(self, code):
            self.code = code

    with patch("app.services.storage_service.S3Error", FakeS3Error):
        storage_service.client.remove_object.side_effect = FakeS3Error("NoSuchKey")
        storage_service.delete("nonexistent/key")


def test_exists_success(storage_service):
    """Test checking if key exists"""
    key = "org_001/sped_efd_icms/abc123.txt"
    storage_service.client.stat_object.return_value = MagicMock()

    assert storage_service.exists(key) is True
    storage_service.client.stat_object.assert_called_once()


def test_exists_not_found(storage_service):
    """Test exists returns False for missing key"""
    class FakeS3Error(Exception):
        def __init__(self, code):
            self.code = code

    with patch("app.services.storage_service.S3Error", FakeS3Error):
        storage_service.client.stat_object.side_effect = FakeS3Error("NoSuchKey")
        assert storage_service.exists("nonexistent/key") is False


# upload_stream tests

async def _async_chunks(data: bytes, chunk_size: int = 1024):
    """Helper: yield data in chunks as async iterator"""
    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]


@pytest.mark.asyncio
async def test_upload_stream_success(storage_service):
    """upload_stream computes hash and size without loading full file in RAM"""
    content = b"chunk1_data" * 500  # ~5.4 KB
    expected_hash = hashlib.sha256(content).hexdigest()
    storage_service.client.put_object.return_value = None

    key, file_hash, file_size = await storage_service.upload_stream(
        file_stream=_async_chunks(content, chunk_size=1024),
        key="org/test/file.txt",
        content_type="text/plain",
    )

    assert file_hash == expected_hash
    assert file_size == len(content)
    assert key == "org/test/file.txt"
    storage_service.client.put_object.assert_called_once()


@pytest.mark.asyncio
async def test_upload_stream_exceeds_max_size(storage_service):
    """upload_stream raises StorageServiceError when file exceeds max_size"""
    content = b"x" * 1000

    with pytest.raises(StorageServiceError, match="exceeds maximum size"):
        await storage_service.upload_stream(
            file_stream=_async_chunks(content, chunk_size=100),
            key="org/test/big.txt",
            content_type="text/plain",
            max_size=500,  # smaller than content
        )


@pytest.mark.asyncio
async def test_upload_stream_empty_file(storage_service):
    """upload_stream handles empty file gracefully"""
    storage_service.client.put_object.return_value = None

    async def empty():
        return
        yield  # make it an async generator

    key, file_hash, file_size = await storage_service.upload_stream(
        file_stream=empty(),
        key="org/test/empty.txt",
        content_type="text/plain",
    )

    assert file_size == 0
    assert len(file_hash) == 64  # valid SHA-256 hex


@pytest.mark.asyncio
async def test_upload_stream_uses_file_object(storage_service):
    """upload_stream passes a readable file-like object to put_object (temp file, not BytesIO)"""
    content = b"fiscal_data" * 200
    storage_service.client.put_object.return_value = None

    await storage_service.upload_stream(
        file_stream=_async_chunks(content, chunk_size=512),
        key="org/test/buffer.txt",
        content_type="text/plain",
    )

    call_args = storage_service.client.put_object.call_args
    stream_arg = call_args[0][2]  # positional: bucket, key, stream, ...
    assert hasattr(stream_arg, "read") and callable(stream_arg.read), (
        "upload_stream must pass a readable file-like object to put_object"
    )


@pytest.mark.asyncio
async def test_upload_stream_correct_length_passed(storage_service):
    """put_object must receive exact byte count as length= keyword argument"""
    content = b"x" * 4096
    storage_service.client.put_object.return_value = None

    _, _, size = await storage_service.upload_stream(
        file_stream=_async_chunks(content, chunk_size=256),
        key="org/test/length_check.txt",
        content_type="text/plain",
    )

    call_kwargs = storage_service.client.put_object.call_args[1]
    assert call_kwargs.get("length") == len(content) == size


@pytest.mark.asyncio
async def test_upload_stream_small_file_no_multipart(storage_service):
    """Files <100 MB must pass part_size=0 (no multipart activation)"""
    content = b"x" * (50 * 1024 * 1024)  # 50 MB — below threshold
    storage_service.client.put_object.return_value = None

    await storage_service.upload_stream(
        file_stream=_async_chunks(content, chunk_size=8 * 1024 * 1024),
        key="org/test/small.txt",
        content_type="text/plain",
    )

    call_kwargs = storage_service.client.put_object.call_args[1]
    assert call_kwargs.get("part_size") == 0, "Small files must not activate multipart"


@pytest.mark.asyncio
async def test_upload_stream_large_file_uses_multipart(storage_service):
    """Files >100 MB must pass part_size>0 to activate MinIO multipart upload"""
    content = b"x" * (101 * 1024 * 1024)  # 101 MB — above threshold
    storage_service.client.put_object.return_value = None

    await storage_service.upload_stream(
        file_stream=_async_chunks(content, chunk_size=8 * 1024 * 1024),
        key="org/test/large.txt",
        content_type="text/plain",
    )

    call_kwargs = storage_service.client.put_object.call_args[1]
    assert call_kwargs.get("part_size", 0) > 0, "Large files must activate multipart via part_size"


@pytest.mark.asyncio
async def test_upload_stream_hash_correctness(storage_service):
    """SHA-256 computed during stream must match hashlib.sha256(content).hexdigest()"""
    content = b"fiscal_document_data_" * 1000
    expected_hash = hashlib.sha256(content).hexdigest()
    storage_service.client.put_object.return_value = None

    _, file_hash, _ = await storage_service.upload_stream(
        file_stream=_async_chunks(content, chunk_size=512),
        key="org/test/hash_check.txt",
        content_type="text/plain",
    )

    assert file_hash == expected_hash


@pytest.mark.asyncio
async def test_upload_stream_returns_correct_key(storage_service):
    """upload_stream must return the exact key passed in (UUID-based, no rename)"""
    content = b"data"
    storage_service.client.put_object.return_value = None
    original_key = "tenant_abc/uploads/550e8400e29b41d4a716446655440000.txt"

    returned_key, _, _ = await storage_service.upload_stream(
        file_stream=_async_chunks(content, chunk_size=512),
        key=original_key,
        content_type="text/plain",
    )

    assert returned_key == original_key, "Key must be returned unchanged (no rename in MinIO)"


@pytest.mark.asyncio
async def test_upload_stream_s3_error_propagates(storage_service):
    """S3Error from put_object must be wrapped as StorageServiceError"""
    from app.services.storage_service import S3Error

    class FakeS3Error(S3Error):
        def __init__(self):
            self.code = "InternalError"
            self.message = "connection reset"
        def __str__(self):
            return self.message

    storage_service.client.put_object.side_effect = FakeS3Error()

    with pytest.raises(StorageServiceError, match="Upload failed"):
        await storage_service.upload_stream(
            file_stream=_async_chunks(b"data", chunk_size=4),
            key="org/test/fail.txt",
            content_type="text/plain",
        )
