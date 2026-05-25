"""
Tests for EPIC 1 — Upload and File Management
"""
import pytest
from io import BytesIO
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.database import Base, get_db
from app.main import app
from app.models.user import User
from app.models.document import Document, DocumentType
from app.services.auth_service import AuthService
from app.services.storage_service import StorageService
from app.schemas.auth import RegisterRequest, LoginRequest
from app.core.config import settings


# In-memory SQLite database for testing
@pytest.fixture
def test_db():
    """Create an in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def test_user(test_db: Session):
    """Create a test user"""
    register_request = RegisterRequest(
        email="test@example.com",
        password="securepassword123",
        full_name="Test User",
        tenant_id="org_001",
    )
    return AuthService.register(test_db, register_request)


@pytest.fixture
def authenticated_client(test_db: Session, test_user: User):
    """Create an authenticated test client"""
    # Login to get tokens
    login_request = LoginRequest(
        email="test@example.com",
        password="securepassword123",
    )
    token_response = AuthService.login(test_db, login_request)

    # Create client with auth headers
    client = TestClient(app)

    # Override get_db dependency
    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    # Add token to headers
    client.headers["Authorization"] = f"Bearer {token_response.access_token}"

    return client


class TestStorageService:
    """Storage service unit tests"""

    def test_calculate_file_hash(self):
        """Test SHA-256 hash calculation"""
        content = b"test file content"
        hash_value = StorageService.calculate_file_hash(content)

        # SHA-256 hash should be 64 hex characters
        assert isinstance(hash_value, str)
        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value)

    def test_calculate_file_hash_consistency(self):
        """Test that same content produces same hash"""
        content = b"test file content"
        hash1 = StorageService.calculate_file_hash(content)
        hash2 = StorageService.calculate_file_hash(content)

        assert hash1 == hash2

    def test_different_content_different_hash(self):
        """Test that different content produces different hash"""
        content1 = b"test file content 1"
        content2 = b"test file content 2"

        hash1 = StorageService.calculate_file_hash(content1)
        hash2 = StorageService.calculate_file_hash(content2)

        assert hash1 != hash2

    def test_build_storage_key(self):
        """Test storage key construction"""
        key = StorageService.build_storage_key(
            tenant_id="org_001",
            document_type="sped_efd_icms",
            file_hash="abc123def456",
            ext="txt"
        )

        assert key == "org_001/sped_efd_icms/abc123def456.txt"

    def test_build_storage_key_default_ext(self):
        """Test storage key with default extension"""
        key = StorageService.build_storage_key(
            tenant_id="org_001",
            document_type="nfe",
            file_hash="abc123def456"
        )

        assert key == "org_001/nfe/abc123def456.txt"


class TestDocumentModel:
    """Document model tests"""

    def test_create_document_record(self, test_db: Session):
        """Test creating a Document record"""
        from app.services.document_service import DocumentService

        doc = DocumentService.create_document_record(
            db=test_db,
            tenant_id="org_001",
            original_filename="test_sped.txt",
            document_type=DocumentType.UNKNOWN,
            file_hash="abc123def456",
            file_size=1024,
            storage_key="org_001/unknown/abc123def456.txt",
            storage_bucket="fiscal-docs",
        )

        assert doc.id is not None
        assert doc.tenant_id == "org_001"
        assert doc.original_filename == "test_sped.txt"
        assert doc.file_hash == "abc123def456"
        assert doc.file_size == 1024
        assert doc.processing_status == "pending"

    def test_document_versioning(self, test_db: Session):
        """Test document versioning on reupload"""
        from app.services.document_service import DocumentService

        # First upload
        doc1 = DocumentService.create_document_record(
            db=test_db,
            tenant_id="org_001",
            original_filename="test_sped.txt",
            document_type=DocumentType.SPED_EFD_ICMS,
            file_hash="abc123def456",
            file_size=1024,
            storage_key="org_001/sped_efd_icms/abc123def456.txt",
            storage_bucket="fiscal-docs",
        )
        db.flush()
        version1 = doc1.document_version

        # Second upload with same hash (reprocessing)
        doc2 = DocumentService.create_document_record(
            db=test_db,
            tenant_id="org_001",
            original_filename="test_sped_v2.txt",
            document_type=DocumentType.SPED_EFD_ICMS,
            file_hash="abc123def456",
            file_size=1024,
            storage_key="org_001/sped_efd_icms/abc123def456.txt",
            storage_bucket="fiscal-docs",
        )

        # First document should be superseded
        test_db.refresh(doc1)
        assert doc1.superseded is True

        # New document should have incremented version
        assert doc2.document_version == version1 + 1


class TestUploadEndpoint:
    """Upload endpoint tests"""

    def test_upload_single_sped_file(self, authenticated_client, test_db: Session):
        """Test uploading a single SPED file"""
        content = b"|0|ID|..."  # Minimal SPED content
        file = ("test_sped.txt", BytesIO(content), "text/plain")

        response = authenticated_client.post(
            "/api/v1/uploads",
            files={"files": file}
        )

        assert response.status_code == 201
        data = response.json()

        assert data["total_files"] == 1
        assert data["summary"]["accepted"] == 1
        assert len(data["results"]) == 1

        result = data["results"][0]
        assert result["filename"] == "test_sped.txt"
        assert result["status"] == "accepted"
        assert "document_id" in result
        assert "job_id" in result
        assert "file_hash" in result

    def test_upload_xml_nfe(self, authenticated_client, test_db: Session):
        """Test uploading an NF-e XML file"""
        content = b'<?xml version="1.0"?><NFe>...</NFe>'
        file = ("nfe.xml", BytesIO(content), "application/xml")

        response = authenticated_client.post(
            "/api/v1/uploads",
            files={"files": file}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["summary"]["accepted"] == 1

    def test_upload_invalid_mime_type(self, authenticated_client):
        """Test that invalid MIME types are rejected"""
        content = b"some binary content"
        file = ("file.bin", BytesIO(content), "application/octet-stream")

        response = authenticated_client.post(
            "/api/v1/uploads",
            files={"files": file}
        )

        assert response.status_code == 201
        data = response.json()

        assert data["summary"]["rejected"] == 1
        result = data["results"][0]
        assert result["status"] == "rejected"
        assert "Invalid file type" in result["reason"]

    def test_upload_no_files(self, authenticated_client):
        """Test upload with no files"""
        response = authenticated_client.post(
            "/api/v1/uploads",
            files={}
        )

        assert response.status_code == 400

    def test_upload_duplicate_file(self, authenticated_client, test_db: Session):
        """Test that duplicate uploads are detected"""
        content = b"|0|ID|test sped content"
        file = ("test_sped.txt", BytesIO(content), "text/plain")

        # First upload
        response1 = authenticated_client.post(
            "/api/v1/uploads",
            files={"files": file}
        )
        assert response1.status_code == 201
        assert response1.json()["summary"]["accepted"] == 1

        # Second upload with same content (will have same hash)
        file = ("test_sped.txt", BytesIO(content), "text/plain")
        response2 = authenticated_client.post(
            "/api/v1/uploads",
            files={"files": file}
        )
        assert response2.status_code == 201

        data = response2.json()
        assert data["summary"]["duplicates"] == 1
        result = data["results"][0]
        assert result["status"] == "duplicate"

    def test_upload_batch_multiple_files(self, authenticated_client):
        """Test batch upload of multiple files"""
        files = [
            ("file1.txt", BytesIO(b"|0|ID|file1"), "text/plain"),
            ("file2.txt", BytesIO(b"|0|ID|file2"), "text/plain"),
            ("file3.xml", BytesIO(b"<?xml></xml>"), "application/xml"),
        ]

        response = authenticated_client.post(
            "/api/v1/uploads",
            files=[(f"files", f) for f in files]
        )

        assert response.status_code == 201
        data = response.json()

        assert data["total_files"] == 3
        assert data["summary"]["accepted"] >= 1

    def test_upload_unauthenticated_fails(self, test_db: Session):
        """Test that unauthenticated upload is rejected"""
        client = TestClient(app)

        def override_get_db():
            yield test_db

        app.dependency_overrides[get_db] = override_get_db

        # No auth header
        content = b"|0|ID|..."
        file = ("test.txt", BytesIO(content), "text/plain")

        response = client.post(
            "/api/v1/uploads",
            files={"files": file}
        )

        assert response.status_code == 403  # Forbidden (no credentials)
