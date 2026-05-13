"""
Dependency injection container for backend services.
Provides centralized service initialization and management.
"""
from functools import lru_cache
from typing import Optional
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.services.voice_service import VoiceService
from app.services.vision_service import VisionService
from app.services.document_service import DocumentService
from app.services.learning_service import MicroSOPService
from app.services.user_service import UserService
from app.services.translation_service import TranslationService
from app.services.whatsapp_service import WhatsAppService
from app.services.sync_service import DataSyncService
from app.services.encryption_service import EncryptionService
from app.services.storage_manager import StorageManager
from app.core.offline_manager import OfflineManager


class ServiceContainer:
    """Container for managing service dependencies"""
    
    def __init__(self, db: Session):
        self.db = db
        self._services = {}
    
    def get_voice_service(self) -> VoiceService:
        """Get or create VoiceService instance"""
        if 'voice' not in self._services:
            self._services['voice'] = VoiceService(self.db)
        return self._services['voice']
    
    def get_vision_service(self) -> VisionService:
        """Get or create VisionService instance"""
        if 'vision' not in self._services:
            self._services['vision'] = VisionService(self.db)
        return self._services['vision']
    
    def get_document_service(self) -> DocumentService:
        """Get or create DocumentService instance"""
        if 'document' not in self._services:
            self._services['document'] = DocumentService(self.db)
        return self._services['document']
    
    def get_learning_service(self) -> MicroSOPService:
        """Get or create MicroSOPService instance"""
        if 'learning' not in self._services:
            self._services['learning'] = MicroSOPService(self.db)
        return self._services['learning']
    
    def get_user_service(self) -> UserService:
        """Get or create UserService instance"""
        if 'user' not in self._services:
            self._services['user'] = UserService(self.db)
        return self._services['user']
    
    def get_translation_service(self) -> TranslationService:
        """Get or create TranslationService instance"""
        if 'translation' not in self._services:
            self._services['translation'] = TranslationService()
        return self._services['translation']
    
    def get_whatsapp_service(self) -> WhatsAppService:
        """Get or create WhatsAppService instance"""
        if 'whatsapp' not in self._services:
            self._services['whatsapp'] = WhatsAppService()
        return self._services['whatsapp']
    
    def get_sync_service(self) -> DataSyncService:
        """Get or create DataSyncService instance"""
        if 'sync' not in self._services:
            self._services['sync'] = DataSyncService()
        return self._services['sync']
    
    def get_encryption_service(self) -> EncryptionService:
        """Get or create EncryptionService instance"""
        if 'encryption' not in self._services:
            self._services['encryption'] = EncryptionService()
        return self._services['encryption']
    
    def get_storage_manager(self) -> StorageManager:
        """Get or create StorageManager instance"""
        if 'storage' not in self._services:
            self._services['storage'] = StorageManager(self.db)
        return self._services['storage']
    
    def get_offline_manager(self) -> OfflineManager:
        """Get or create OfflineManager instance"""
        if 'offline' not in self._services:
            self._services['offline'] = OfflineManager(self.db)
        return self._services['offline']


def get_service_container(db: Session = None) -> ServiceContainer:
    """Get service container instance"""
    if db is None:
        db = next(get_db())
    return ServiceContainer(db)
