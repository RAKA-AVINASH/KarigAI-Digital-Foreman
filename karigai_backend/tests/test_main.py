import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from app.core.database import get_db, Base

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create test database
Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def test_root():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "KarigAI API is running"


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_supported_languages():
    """Test supported languages endpoint"""
    response = client.get("/api/v1/voice/supported-languages")
    assert response.status_code == 200
    assert "supported_languages" in response.json()
    assert "hi-IN" in response.json()["supported_languages"]


def test_course_categories():
    """Test course categories endpoint"""
    response = client.get("/api/v1/learning/categories")
    assert response.status_code == 200
    assert "categories" in response.json()
    assert "carpentry" in response.json()["categories"]


def test_document_templates():
    """Test document templates endpoint"""
    response = client.get("/api/v1/documents/templates/available")
    assert response.status_code == 200
    assert "templates" in response.json()
    assert "default" in response.json()["templates"]