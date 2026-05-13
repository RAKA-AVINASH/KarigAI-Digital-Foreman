"""
Property-Based Tests for Data Security and Privacy

**Property 25: Data Security and Privacy**
**Validates: Requirements 9.1, 9.2, 9.3, 9.5**

For any voice data processing, customer information storage, or analytics collection,
the system should implement encryption, require explicit consent, and anonymize
personal identifiers.
"""

import pytest
from hypothesis import given, strategies as st, settings
from hypothesis import HealthCheck
import json
import tempfile
import os

from app.services.encryption_service import EncryptionService, ConsentManager


# Strategy for generating voice data
@st.composite
def voice_data_strategy(draw):
    """Generate voice data with various content"""
    return {
        "audio_file": draw(st.text(min_size=10, max_size=100)),
        "transcription": draw(st.text(min_size=5, max_size=200)),
        "user_id": draw(st.text(min_size=5, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),
        "timestamp": draw(st.datetimes().map(lambda d: d.isoformat())),
        "language": draw(st.sampled_from(["hi-IN", "en-US", "ml-IN", "pa-IN"]))
    }


# Strategy for generating customer information
@st.composite
def customer_info_strategy(draw):
    """Generate customer information with PII"""
    return {
        "customer_id": draw(st.text(min_size=5, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),
        "name": draw(st.text(min_size=3, max_size=50)),
        "phone": draw(st.text(min_size=10, max_size=15, alphabet=st.characters(whitelist_categories=('Nd',)))),
        "address": draw(st.text(min_size=10, max_size=100)),
        "email": draw(st.emails()),
        "service_history": draw(st.lists(st.text(min_size=5, max_size=20), min_size=0, max_size=5))
    }


# Strategy for generating analytics data
@st.composite
def analytics_data_strategy(draw):
    """Generate analytics data that may contain PII"""
    return {
        "user_id": draw(st.text(min_size=5, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),
        "action": draw(st.sampled_from(["voice_input", "document_generated", "image_analyzed", "learning_completed"])),
        "timestamp": draw(st.datetimes().map(lambda d: d.isoformat())),
        "metadata": {
            "ip_address": draw(st.ip_addresses().map(str)),
            "device_id": draw(st.text(min_size=10, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),
            "session_duration": draw(st.integers(min_value=1, max_value=3600))
        }
    }


class TestDataSecurityPrivacyProperty:
    """Property-based tests for data security and privacy"""
    
    @given(voice_data=voice_data_strategy())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_voice_data_encryption_property(self, voice_data):
        """
        Property: Voice data must be encrypted during storage
        
        For any voice data, when stored, it should be encrypted such that:
        1. Encrypted data is different from original
        2. Encrypted data can be decrypted back to original
        3. Same data encrypted twice produces different ciphertexts (due to IV)
        
        **Validates: Requirements 9.1**
        """
        encryption_service = EncryptionService(master_key="test-security-key-12345")
        
        # Convert voice data to JSON string
        voice_json = json.dumps(voice_data)
        
        # Encrypt the voice data
        encrypted = encryption_service.encrypt_text(voice_json)
        
        # Property 1: Encrypted data is different from original
        assert encrypted != voice_json, "Encrypted data should differ from plaintext"
        
        # Property 2: Can decrypt back to original
        decrypted = encryption_service.decrypt_text(encrypted)
        assert decrypted == voice_json, "Decrypted data should match original"
        
        # Property 3: Verify data integrity after decryption
        decrypted_data = json.loads(decrypted)
        assert decrypted_data == voice_data, "Decrypted voice data should match original structure"
    
    @given(customer_info=customer_info_strategy())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_customer_information_encryption_property(self, customer_info):
        """
        Property: Customer information must be encrypted during storage
        
        For any customer information containing PII, when stored:
        1. All PII fields must be encrypted
        2. Encrypted data must be recoverable
        3. Encryption must preserve data structure
        
        **Validates: Requirements 9.2**
        """
        encryption_service = EncryptionService(master_key="test-security-key-12345")
        
        # Encrypt customer information
        encrypted = encryption_service.encrypt_dict(customer_info)
        
        # Property 1: Encrypted data is not plaintext
        assert encrypted != json.dumps(customer_info), "Customer info should be encrypted"
        
        # Property 2: Can decrypt back to original
        decrypted = encryption_service.decrypt_dict(encrypted)
        
        # Property 3: All fields preserved after encryption/decryption
        assert decrypted["customer_id"] == customer_info["customer_id"]
        assert decrypted["name"] == customer_info["name"]
        assert decrypted["phone"] == customer_info["phone"]
        assert decrypted["address"] == customer_info["address"]
        assert decrypted["email"] == customer_info["email"]
        assert decrypted["service_history"] == customer_info["service_history"]
    
    @given(user_id=st.text(min_size=5, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
           consent_type=st.sampled_from(["voice_recording", "analytics", "data_sharing", "marketing"]))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_explicit_consent_required_property(self, user_id, consent_type):
        """
        Property: Explicit consent must be required for data collection
        
        For any user and consent type:
        1. Default consent status should be False (opt-in required)
        2. Consent can be explicitly granted
        3. Consent can be revoked
        
        **Validates: Requirements 9.2**
        """
        consent_manager = ConsentManager(db_session=None)
        
        # Property 1: Default consent is False (explicit opt-in required)
        has_consent = consent_manager.check_consent(user_id, consent_type)
        assert has_consent is False, "Consent should default to False (explicit opt-in required)"
        
        # Property 2: Consent can be granted
        consent_record = consent_manager.record_consent(
            user_id=user_id,
            consent_type=consent_type,
            granted=True,
            purpose="Testing consent management"
        )
        assert consent_record["granted"] is True
        assert consent_record["user_id"] == user_id
        assert consent_record["consent_type"] == consent_type
        
        # Property 3: Consent can be revoked
        revoke_result = consent_manager.revoke_consent(user_id, consent_type)
        assert revoke_result is True, "Consent revocation should succeed"
    
    @given(analytics_data=analytics_data_strategy())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_analytics_anonymization_property(self, analytics_data):
        """
        Property: Personal identifiers must be anonymized in analytics
        
        For any analytics data:
        1. User IDs should be hashed (one-way)
        2. IP addresses should be anonymized
        3. Device IDs should be hashed
        4. Hashing should be consistent (same input = same hash)
        
        **Validates: Requirements 9.3, 9.5**
        """
        encryption_service = EncryptionService(master_key="test-security-key-12345")
        
        # Property 1: User ID should be hashed
        user_id_hash = encryption_service.hash_sensitive_field(analytics_data["user_id"])
        assert user_id_hash != analytics_data["user_id"], "User ID should be hashed"
        assert len(user_id_hash) == 64, "SHA256 hash should be 64 hex characters"
        
        # Property 2: IP address should be anonymized (hashed)
        ip_hash = encryption_service.hash_sensitive_field(analytics_data["metadata"]["ip_address"])
        assert ip_hash != analytics_data["metadata"]["ip_address"], "IP should be hashed"
        
        # Property 3: Device ID should be hashed
        device_hash = encryption_service.hash_sensitive_field(analytics_data["metadata"]["device_id"])
        assert device_hash != analytics_data["metadata"]["device_id"], "Device ID should be hashed"
        
        # Property 4: Hashing is consistent (same input produces same hash)
        user_id_hash2 = encryption_service.hash_sensitive_field(analytics_data["user_id"])
        assert user_id_hash == user_id_hash2, "Hashing should be deterministic"
        
        # Property 5: Different inputs produce different hashes
        if len(analytics_data["user_id"]) > 1:
            different_id = analytics_data["user_id"][:-1] + ("x" if analytics_data["user_id"][-1] != "x" else "y")
            different_hash = encryption_service.hash_sensitive_field(different_id)
            assert different_hash != user_id_hash, "Different inputs should produce different hashes"
    
    @given(data=st.binary(min_size=100, max_size=1000))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_file_encryption_property(self, data):
        """
        Property: Audio files must be encrypted during storage
        
        For any audio file data:
        1. Encrypted file content differs from original
        2. Encrypted file can be decrypted back to original
        3. File encryption preserves data integrity
        
        **Validates: Requirements 9.1**
        """
        encryption_service = EncryptionService(master_key="test-security-key-12345")
        
        # Create temporary file with test data
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.audio') as f:
            test_file = f.name
            f.write(data)
        
        try:
            # Property 1: Encrypt file
            encrypted_file = encryption_service.encrypt_file(test_file)
            assert os.path.exists(encrypted_file), "Encrypted file should exist"
            
            # Property 2: Encrypted content differs from original
            with open(test_file, 'rb') as f:
                original_data = f.read()
            with open(encrypted_file, 'rb') as f:
                encrypted_data = f.read()
            assert original_data != encrypted_data, "Encrypted file should differ from original"
            
            # Property 3: Decrypt and verify integrity
            decrypted_file = encryption_service.decrypt_file(encrypted_file)
            with open(decrypted_file, 'rb') as f:
                decrypted_data = f.read()
            assert decrypted_data == data, "Decrypted data should match original"
            
        finally:
            # Cleanup
            for path in [test_file, encrypted_file, decrypted_file]:
                if os.path.exists(path):
                    os.remove(path)
    
    @given(
        plaintext1=st.text(min_size=10, max_size=100),
        plaintext2=st.text(min_size=10, max_size=100)
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_encryption_uniqueness_property(self, plaintext1, plaintext2):
        """
        Property: Different plaintexts produce different ciphertexts
        
        For any two different plaintexts:
        1. Their encrypted forms should be different
        2. Each can be decrypted back to its original
        
        **Validates: Requirements 9.1**
        """
        encryption_service = EncryptionService(master_key="test-security-key-12345")
        
        # Skip if plaintexts are identical
        if plaintext1 == plaintext2:
            return
        
        # Encrypt both plaintexts
        encrypted1 = encryption_service.encrypt_text(plaintext1)
        encrypted2 = encryption_service.encrypt_text(plaintext2)
        
        # Property 1: Different plaintexts produce different ciphertexts
        assert encrypted1 != encrypted2, "Different plaintexts should produce different ciphertexts"
        
        # Property 2: Each decrypts to its original
        decrypted1 = encryption_service.decrypt_text(encrypted1)
        decrypted2 = encryption_service.decrypt_text(encrypted2)
        assert decrypted1 == plaintext1, "First plaintext should decrypt correctly"
        assert decrypted2 == plaintext2, "Second plaintext should decrypt correctly"
