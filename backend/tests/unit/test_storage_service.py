"""
Tests for StorageService (MinIO abstraction)
"""
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
