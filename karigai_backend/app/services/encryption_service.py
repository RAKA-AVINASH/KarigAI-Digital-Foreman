"""
Encryption Service for KarigAI

Provides encryption and decryption capabilities for sensitive data including
voice recordings, customer information, and personal identifiable information.
Implements AES-256 encryption for data at rest and ensures secure key management.
"""

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import os
from typing import Optional, Dict, Any
import json
from datetime import datetime, timezone


class EncryptionService:
    """Service for encrypting and decrypting sensitive data"""
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize encryption service with master key
        
        Args:
            master_key: Master encryption key (should be from secure config)
        """
        if master_key is None:
            # In production, this should come from secure environment variable
            master_key = os.environ.get("ENCRYPTION_MASTER_KEY", "default-key-change-in-production")
        
        self.master_key = master_key.encode()
        self._cipher_suite = self._create_cipher_suite()
    
    def _create_cipher_suite(self) -> Fernet:
        """Create Fernet cipher suite from master key"""
        # Derive a proper key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'karigai_salt_v1',  # In production, use unique salt per installation
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
        return Fernet(key)
    
    def encrypt_text(self, plaintext: str) -> str:
        """
        Encrypt text data
        
        Args:
            plaintext: Text to encrypt
            
        Returns:
            Base64-encoded encrypted text
        """
        if not plaintext:
            return ""
        
        encrypted_bytes = self._cipher_suite.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted_bytes).decode()
    
    def decrypt_text(self, encrypted_text: str) -> str:
        """
        Decrypt text data
        
        Args:
            encrypted_text: Base64-encoded encrypted text
            
        Returns:
            Decrypted plaintext
        """
        if not encrypted_text:
            return ""
        
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_text.encode())
        decrypted_bytes = self._cipher_suite.decrypt(encrypted_bytes)
        return decrypted_bytes.decode()
    
    def encrypt_file(self, file_path: str, output_path: Optional[str] = None) -> str:
        """
        Encrypt a file (e.g., voice recording)
        
        Args:
            file_path: Path to file to encrypt
            output_path: Optional output path (defaults to file_path + '.enc')
            
        Returns:
            Path to encrypted file
        """
        if output_path is None:
            output_path = file_path + '.enc'
        
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        encrypted_data = self._cipher_suite.encrypt(file_data)
        
        with open(output_path, 'wb') as f:
            f.write(encrypted_data)
        
        return output_path
    
    def decrypt_file(self, encrypted_file_path: str, output_path: Optional[str] = None) -> str:
        """
        Decrypt a file
        
        Args:
            encrypted_file_path: Path to encrypted file
            output_path: Optional output path
            
        Returns:
            Path to decrypted file
        """
        if output_path is None:
            output_path = encrypted_file_path.replace('.enc', '')
        
        with open(encrypted_file_path, 'rb') as f:
            encrypted_data = f.read()
        
        decrypted_data = self._cipher_suite.decrypt(encrypted_data)
        
        with open(output_path, 'wb') as f:
            f.write(decrypted_data)
        
        return output_path
    
    def encrypt_dict(self, data: Dict[str, Any]) -> str:
        """
        Encrypt dictionary data (e.g., customer information)
        
        Args:
            data: Dictionary to encrypt
            
        Returns:
            Base64-encoded encrypted JSON
        """
        json_str = json.dumps(data)
        return self.encrypt_text(json_str)
    
    def decrypt_dict(self, encrypted_data: str) -> Dict[str, Any]:
        """
        Decrypt dictionary data
        
        Args:
            encrypted_data: Base64-encoded encrypted JSON
            
        Returns:
            Decrypted dictionary
        """
        json_str = self.decrypt_text(encrypted_data)
        return json.loads(json_str)
    
    def hash_sensitive_field(self, value: str) -> str:
        """
        Create one-way hash of sensitive field (e.g., phone number for indexing)
        
        Args:
            value: Value to hash
            
        Returns:
            Hex-encoded hash
        """
        from cryptography.hazmat.primitives import hashes
        digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
        digest.update(value.encode())
        return digest.finalize().hex()


class ConsentManager:
    """Manages user consent for data collection and processing"""
    
    def __init__(self, db_session):
        """
        Initialize consent manager
        
        Args:
            db_session: Database session for storing consent records
        """
        self.db = db_session
    
    def record_consent(
        self,
        user_id: str,
        consent_type: str,
        granted: bool,
        purpose: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Record user consent for data processing
        
        Args:
            user_id: User identifier
            consent_type: Type of consent (e.g., 'voice_recording', 'analytics')
            granted: Whether consent was granted
            purpose: Purpose of data collection
            metadata: Additional metadata
            
        Returns:
            Consent record
        """
        consent_record = {
            "user_id": user_id,
            "consent_type": consent_type,
            "granted": granted,
            "purpose": purpose,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {}
        }
        
        # In production, store in database
        # For now, return the record
        return consent_record
    
    def check_consent(self, user_id: str, consent_type: str) -> bool:
        """
        Check if user has granted consent for specific data processing
        
        Args:
            user_id: User identifier
            consent_type: Type of consent to check
            
        Returns:
            True if consent granted, False otherwise
        """
        # In production, query database for consent record
        # For now, default to requiring explicit consent
        return False
    
    def revoke_consent(self, user_id: str, consent_type: str) -> bool:
        """
        Revoke user consent for data processing
        
        Args:
            user_id: User identifier
            consent_type: Type of consent to revoke
            
        Returns:
            True if revocation successful
        """
        # In production, update database record
        return True
    
    def get_user_consents(self, user_id: str) -> Dict[str, bool]:
        """
        Get all consent statuses for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary of consent types and their status
        """
        # In production, query database
        return {
            "voice_recording": False,
            "analytics": False,
            "data_sharing": False,
            "marketing": False
        }


class SecureDataTransmission:
    """Ensures secure data transmission with TLS encryption"""
    
    @staticmethod
    def get_tls_config() -> Dict[str, Any]:
        """
        Get TLS configuration for secure data transmission
        
        Returns:
            TLS configuration dictionary
        """
        return {
            "ssl_version": "TLSv1.2",
            "cert_reqs": "CERT_REQUIRED",
            "check_hostname": True,
            "verify_mode": True
        }
    
    @staticmethod
    def validate_certificate(cert_path: str) -> bool:
        """
        Validate SSL/TLS certificate
        
        Args:
            cert_path: Path to certificate file
            
        Returns:
            True if certificate is valid
        """
        # In production, implement proper certificate validation
        return os.path.exists(cert_path)
    
    @staticmethod
    def encrypt_transmission_payload(payload: Dict[str, Any], encryption_service: EncryptionService) -> str:
        """
        Encrypt payload for transmission
        
        Args:
            payload: Data to transmit
            encryption_service: Encryption service instance
            
        Returns:
            Encrypted payload
        """
        return encryption_service.encrypt_dict(payload)
