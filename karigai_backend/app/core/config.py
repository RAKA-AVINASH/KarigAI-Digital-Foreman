from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List, Optional
import os


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", case_sensitive=True, extra="ignore")
    
    # Application
    APP_NAME: str = "KarigAI API"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database
    DATABASE_URL: str = "sqlite:///./karigai.db"
    POSTGRES_URL: Optional[str] = None
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]
    
    # AI Services
    OPENAI_API_KEY: Optional[str] = None
    GOOGLE_CLOUD_PROJECT: Optional[str] = None
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None
    ELEVENLABS_API_KEY: Optional[str] = None
    
    # WhatsApp/Twilio
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_WHATSAPP_NUMBER: Optional[str] = None
    
    # File Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # Performance
    VOICE_PROCESSING_TIMEOUT: int = 3
    DOCUMENT_GENERATION_TIMEOUT: int = 5
    IMAGE_ANALYSIS_TIMEOUT: int = 10
    
    # Supported Languages
    SUPPORTED_LANGUAGES: List[str] = [
        "hi-IN",  # Hindi
        "en-US",  # English
        "ml-IN",  # Malayalam
        "pa-IN",  # Punjabi
        "bn-IN",  # Bengali
        "ta-IN",  # Tamil
        "te-IN",  # Telugu
    ]


settings = Settings()