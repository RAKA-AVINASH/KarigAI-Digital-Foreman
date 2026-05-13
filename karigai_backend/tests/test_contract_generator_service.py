"""
Unit tests for Contract Generator Service

Tests contract term extraction, Work Order Agreement generation,
and digital signature functionality.
"""

import pytest
import os
import tempfile
import json
from datetime import datetime

from app.services.contract_generator_service import (
    ContractGeneratorService,
    ContractTerms,
    DigitalSignature
)


@pytest.fixture
def contract_service():
    """Create contract generator service with temp directory"""
    temp_dir = tempfile.mkdtemp()
    service = ContractGeneratorService(output_dir=temp_dir)
    yield service


@pytest.fixture
def sample_transcription():
    """Sample verbal agreement transcription"""
    return """
    I agree to repair the plumbing system for Rs 5000. 
    The work includes fixing the leaking pipes and installing new faucets.
    I will complete the work in 3 days.
    Payment will be 50% advance and 50% on completion.
    Materials are included in the price.
    """


@pytest.fixture
def sample_contract_terms():
    """Sample contract terms"""
    return ContractTerms(
        amount=5000.0,
        scope_of_work="Repair plumbing system including fixing leaking pipes and installing new faucets",
        timeline="3 days",
        party_a_name="Ramesh Kumar",
        party_a_contact="+919876543210",
        party_b_name="Suresh Sharma",
        party_b_contact="+919876543211",
        payment_terms="50% advance, 50% on completion",
        materials_included=True,
        additional_terms=["Warranty: 90 days", "Working hours: 9 AM to 5 PM"]
    )


class TestContractTermExtraction:
    """Test contract term extraction from transcriptions"""
    
    def test_extract_amount(self, contract_service, sample_transcription):
        """Test extracting monetary amount"""
        terms = contract_service.extract_contract_terms(sample_transcription)
        assert terms.amount == 5000.0
    
    def test_extract_scope(self, contract_service, sample_transcription):
        """Test extracting scope of work"""
        terms = contract_service.extract_contract_terms(sample_transcription)
        assert "repair" in terms.scope_of_work.lower()
    
    def test_extract_timeline(self, contract_service, sample_transcription):
        """Test extracting timeline"""
        terms = contract_service.extract_contract_terms(sample_transcription)
        assert "3 days" in terms.timeline.lower()
    
    def test_extract_payment_terms(self, contract_service, sample_transcription):
        """Test extracting payment terms"""
        terms = contract_service.extract_contract_terms(sample_transcription)
        assert terms.payment_terms is not None
        assert "payment" in terms.payment_terms.lower()
    
    def test_extract_materials_included(self, contract_service, sample_transcription):
        """Test detecting materials inclusion"""
        terms = contract_service.extract_contract_terms(sample_transcription)
        assert terms.materials_included is True
    
    def test_extract_with_context(self, contract_service):
        """Test extraction with additional context"""
        context = {
            "party_a_name": "Ramesh Kumar",
            "party_a_contact": "+919876543210",
            "party_b_name": "Suresh Sharma",
            "party_b_contact": "+919876543211"
        }
        
        terms = contract_service.extract_contract_terms(
            "I will do the work for Rs 1000",
            context=context
        )
        
        assert terms.party_a_name == "Ramesh Kumar"
        assert terms.party_b_name == "Suresh Sharma"


class TestWorkOrderAgreementGeneration:
    """Test Work Order Agreement PDF generation"""
    
    @pytest.mark.asyncio
    async def test_generate_agreement_creates_file(self, contract_service, sample_contract_terms):
        """Test that agreement generation creates a PDF file"""
        pdf_doc = await contract_service.generate_work_order_agreement(sample_contract_terms)
        
        assert os.path.exists(pdf_doc.file_path)
        assert pdf_doc.file_path.endswith(".pdf")
    
    @pytest.mark.asyncio
    async def test_generate_agreement_metadata(self, contract_service, sample_contract_terms):
        """Test agreement metadata is correct"""
        pdf_doc = await contract_service.generate_work_order_agreement(sample_contract_terms)
        
        assert "WOA-" in pdf_doc.metadata["contract_id"]
        assert pdf_doc.metadata["amount"] == 5000.0
        assert pdf_doc.metadata["party_a"] == "Ramesh Kumar"
        assert pdf_doc.metadata["party_b"] == "Suresh Sharma"
    
    @pytest.mark.asyncio
    async def test_generate_agreement_bilingual(self, contract_service, sample_contract_terms):
        """Test agreement generation in both languages"""
        pdf_hindi = await contract_service.generate_work_order_agreement(
            sample_contract_terms, 
            language="hi-IN"
        )
        pdf_english = await contract_service.generate_work_order_agreement(
            sample_contract_terms, 
            language="en-IN"
        )
        
        assert os.path.exists(pdf_hindi.file_path)
        assert os.path.exists(pdf_english.file_path)
        assert "hi-IN" in pdf_hindi.file_path
        assert "en-IN" in pdf_english.file_path
    
    @pytest.mark.asyncio
    async def test_generate_agreement_with_custom_id(self, contract_service, sample_contract_terms):
        """Test agreement generation with custom contract ID"""
        custom_id = "WOA-CUSTOM-001"
        pdf_doc = await contract_service.generate_work_order_agreement(
            sample_contract_terms,
            contract_id=custom_id
        )
        
        assert pdf_doc.metadata["contract_id"] == custom_id
        assert custom_id in pdf_doc.file_path
    
    @pytest.mark.asyncio
    async def test_generate_agreement_minimal_terms(self, contract_service):
        """Test agreement generation with minimal terms"""
        minimal_terms = ContractTerms(
            amount=1000.0,
            scope_of_work="Basic repair work",
            timeline="1 day",
            party_a_name="Party A",
            party_a_contact=None,
            party_b_name="Party B",
            party_b_contact=None
        )
        
        pdf_doc = await contract_service.generate_work_order_agreement(minimal_terms)
        
        assert os.path.exists(pdf_doc.file_path)
        assert pdf_doc.metadata["amount"] == 1000.0


class TestDigitalSignature:
    """Test digital signature functionality"""
    
    def test_create_digital_signature(self, contract_service):
        """Test creating a digital signature"""
        signature = contract_service.create_digital_signature(
            signer_name="Ramesh Kumar",
            signer_contact="+919876543210",
            contract_id="WOA-TEST-001"
        )
        
        assert signature.signer_name == "Ramesh Kumar"
        assert signature.signer_contact == "+919876543210"
        assert signature.signature_hash is not None
        assert len(signature.signature_hash) == 64  # SHA256 hash length
    
    def test_create_signature_with_location(self, contract_service):
        """Test creating signature with location data"""
        location_data = {
            "latitude": 28.6139,
            "longitude": 77.2090,
            "address": "New Delhi, India"
        }
        
        signature = contract_service.create_digital_signature(
            signer_name="Ramesh Kumar",
            signer_contact="+919876543210",
            contract_id="WOA-TEST-001",
            location_data=location_data
        )
        
        assert signature.location_data is not None
        assert signature.location_data["latitude"] == 28.6139
    
    def test_signature_hash_uniqueness(self, contract_service):
        """Test that different signatures have different hashes"""
        sig1 = contract_service.create_digital_signature(
            signer_name="Person A",
            signer_contact="+919876543210",
            contract_id="WOA-TEST-001"
        )
        
        sig2 = contract_service.create_digital_signature(
            signer_name="Person B",
            signer_contact="+919876543211",
            contract_id="WOA-TEST-001"
        )
        
        assert sig1.signature_hash != sig2.signature_hash


class TestContractStorage:
    """Test secure contract storage"""
    
    @pytest.mark.asyncio
    async def test_store_contract_securely(self, contract_service, sample_contract_terms):
        """Test storing contract with signatures"""
        # Generate contract
        pdf_doc = await contract_service.generate_work_order_agreement(sample_contract_terms)
        
        # Create signatures
        sig1 = contract_service.create_digital_signature(
            signer_name="Ramesh Kumar",
            signer_contact="+919876543210",
            contract_id=pdf_doc.metadata["contract_id"]
        )
        
        sig2 = contract_service.create_digital_signature(
            signer_name="Suresh Sharma",
            signer_contact="+919876543211",
            contract_id=pdf_doc.metadata["contract_id"]
        )
        
        # Store contract
        storage_record = contract_service.store_contract_securely(
            contract_id=pdf_doc.metadata["contract_id"],
            pdf_path=pdf_doc.file_path,
            signatures=[sig1, sig2],
            metadata=pdf_doc.metadata
        )
        
        assert storage_record["contract_id"] == pdf_doc.metadata["contract_id"]
        assert len(storage_record["signatures"]) == 2
        assert storage_record["stored_at"] is not None
    
    @pytest.mark.asyncio
    async def test_storage_file_created(self, contract_service, sample_contract_terms):
        """Test that storage file is created"""
        # Generate contract
        pdf_doc = await contract_service.generate_work_order_agreement(sample_contract_terms)
        
        # Create signature
        sig = contract_service.create_digital_signature(
            signer_name="Ramesh Kumar",
            signer_contact="+919876543210",
            contract_id=pdf_doc.metadata["contract_id"]
        )
        
        # Store contract
        storage_record = contract_service.store_contract_securely(
            contract_id=pdf_doc.metadata["contract_id"],
            pdf_path=pdf_doc.file_path,
            signatures=[sig],
            metadata=pdf_doc.metadata
        )
        
        # Verify storage file exists
        storage_file = f"{contract_service.output_dir}/{pdf_doc.metadata['contract_id']}_storage.json"
        assert os.path.exists(storage_file)
        
        # Verify storage file content
        with open(storage_file, 'r') as f:
            stored_data = json.load(f)
            assert stored_data["contract_id"] == pdf_doc.metadata["contract_id"]
            assert len(stored_data["signatures"]) == 1
