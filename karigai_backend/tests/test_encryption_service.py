"""
Unit tests for Encryption Service
"""

import pytest
import os
import tempfile
import json
from app.services.encryption_service import (
    EncryptionService,
    ConsentManager,
    SecureDataTransmission
)


class TestEncryptionService:
    """Test encryption service functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.encryption_service = EncryptionService(master_key="test-master-key-12345")
    
    def test_encrypt_decrypt_text(self):
        """Test text encryption and decryption"""
        plaintext = "Sensitive customer information"
        
        encrypted = self.encryption_service.encrypt_text(plaintext)
        assert encrypted != plaintext
        assert len(encrypted) > 0
        
        decrypted = self.encryption_service.decrypt_text(encrypted)
        assert decrypted == plaintext
    
    def test_encrypt_empty_text(self):
        """Test encryption of empty text"""
        encrypted = self.encryption_service.encrypt_text("")
        assert encrypted == ""
        
        decrypted = self.encryption_service.decrypt_text("")
        assert decrypted == ""
    
    def test_encrypt_decrypt_dict(self):
        """Test dictionary encryption and decryption"""
        customer_data = {
            "name": "राज कुमार",
            "phone": "+91-9876543210",
            "address": "123 Main St, Bhopal",
            "service_history": ["repair_1", "repair_2"]
        }
        
        encrypted = self.encryption_service.encrypt_dict(customer_data)
        assert encrypted != json.dumps(customer_data)
        
        decrypted = self.encryption_service.decrypt_dict(encrypted)
        assert decrypted == customer_data
    
    def test_encrypt_decrypt_file(self):
        """Test file encryption and decryption"""
        # Create temporary file with test data
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            test_file = f.name
            f.write("Voice recording data: sensitive audio content")
        
        try:
            # Encrypt file
            encrypted_file = self.encryption_service.encrypt_file(test_file)
            assert os.path.exists(encrypted_file)
            assert encrypted_file.endswith('.enc')
            
            # Verify encrypted content is different
            with open(test_file, 'rb') as f:
                original_data = f.read()
            with open(encrypted_file, 'rb') as f:
                encrypted_data = f.read()
            assert original_data != encrypted_data
            
            # Decrypt file
            decrypted_file = self.encryption_service.decrypt_file(encrypted_file)
            assert os.path.exists(decrypted_file)
            
            # Verify decrypted content matches original
            with open(decrypted_file, 'r') as f:
                decrypted_content = f.read()
            assert decrypted_content == "Voice recording data: sensitive audio content"
            
        finally:
            # Cleanup
            if os.path.exists(test_file):
                os.remove(test_file)
            if os.path.exists(encrypted_file):
                os.remove(encrypted_file)
            if os.path.exists(decrypted_file):
                os.remove(decrypted_file)
    
    def test_hash_sensitive_field(self):
        """Test one-way hashing of sensitive fields"""
        phone_number = "+91-9876543210"
        
        hash1 = self.encryption_service.hash_sensitive_field(phone_number)
        hash2 = self.encryption_service.hash_sensitive_field(phone_number)
        
        # Same input produces same hash
        assert hash1 == hash2
        
        # Hash is different from original
        assert hash1 != phone_number
        
        # Hash is consistent length
        assert len(hash1) == 64  # SHA256 hex = 64 chars
    
    def test_different_plaintexts_produce_different_ciphertexts(self):
        """Test that different inputs produce different encrypted outputs"""
        text1 = "Customer A data"
        text2 = "Customer B data"
        
        encrypted1 = self.encryption_service.encrypt_text(text1)
        encrypted2 = self.encryption_service.encrypt_text(text2)
        
        assert encrypted1 != encrypted2


class TestConsentManager:
    """Test consent management functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.consent_manager = ConsentManager(db_session=None)
    
    def test_record_consent(self):
        """Test recording user consent"""
        consent = self.consent_manager.record_consent(
            user_id="user123",
            consent_type="voice_recording",
            granted=True,
            purpose="Invoice generation and troubleshooting"
        )
        
        assert consent["user_id"] == "user123"
        assert consent["consent_type"] == "voice_recording"
        assert consent["granted"] is True
        assert consent["purpose"] == "Invoice generation and troubleshooting"
        assert "timestamp" in consent
    
    def test_record_consent_with_metadata(self):
        """Test recording consent with additional metadata"""
        metadata = {
            "ip_address": "192.168.1.1",
            "user_agent": "KarigAI Mobile App v1.0"
        }
        
        consent = self.consent_manager.record_consent(
            user_id="user456",
            consent_type="analytics",
            granted=False,
            purpose="Usage analytics",
            metadata=metadata
        )
        
        assert consent["metadata"] == metadata
    
    def test_check_consent_default_false(self):
        """Test that consent check defaults to False (explicit consent required)"""
        has_consent = self.consent_manager.check_consent("user789", "voice_recording")
        assert has_consent is False
    
    def test_revoke_consent(self):
        """Test revoking user consent"""
        result = self.consent_manager.revoke_consent("user123", "analytics")
        assert result is True
    
    def test_get_user_consents(self):
        """Test retrieving all user consents"""
        consents = self.consent_manager.get_user_consents("user123")
        
        assert isinstance(consents, dict)
        assert "voice_recording" in consents
        assert "analytics" in consents
        assert "data_sharing" in consents


class TestSecureDataTransmission:
    """Test secure data transmission utilities"""
    
    def test_get_tls_config(self):
        """Test TLS configuration retrieval"""
        config = SecureDataTransmission.get_tls_config()
        
        assert "ssl_version" in config
        assert config["ssl_version"] == "TLSv1.2"
        assert config["cert_reqs"] == "CERT_REQUIRED"
        assert config["check_hostname"] is True
    
    def test_encrypt_transmission_payload(self):
        """Test payload encryption for transmission"""
        encryption_service = EncryptionService(master_key="test-key")
        payload = {
            "user_id": "user123",
            "voice_data": "transcribed text",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        encrypted_payload = SecureDataTransmission.encrypt_transmission_payload(
            payload, encryption_service
        )
        
        assert encrypted_payload != json.dumps(payload)
        assert len(encrypted_payload) > 0
        
        # Verify can decrypt
        decrypted = encryption_service.decrypt_dict(encrypted_payload)
        assert decrypted == payload
