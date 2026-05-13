"""
Unit tests for Authenticity Service

Tests production record creation, Digital Story Card generation,
and blockchain-based verification.
"""

import pytest
import os
import tempfile
import json
from datetime import datetime

from app.services.authenticity_service import (
    AuthenticityService,
    ProductionRecord
)


@pytest.fixture
def auth_service():
    """Create authenticity service with temp directory"""
    temp_dir = tempfile.mkdtemp()
    service = AuthenticityService(output_dir=temp_dir)
    yield service


@pytest.fixture
def sample_production_record(auth_service):
    """Create sample production record"""
    return auth_service.create_production_record(
        product_name="Handwoven Pashmina Shawl",
        product_category="Pashmina",
        craftsman_name="Mohammad Yusuf",
        craftsman_contact="+919876543210",
        location="Srinagar, Jammu & Kashmir",
        materials=["Pure Pashmina wool", "Natural dyes"],
        techniques=["Hand spinning", "Traditional weaving"],
        description="Authentic Kashmiri Pashmina shawl handwoven using traditional techniques"
    )


class TestProductionRecord:
    """Test production record creation"""
    
    def test_create_production_record(self, auth_service):
        """Test creating a production record"""
        record = auth_service.create_production_record(
            product_name="Test Product",
            product_category="Test Category",
            craftsman_name="Test Craftsman",
            craftsman_contact="+919876543210",
            location="Test Location"
        )
        
        assert record.product_name == "Test Product"
        assert record.craftsman_name == "Test Craftsman"
        assert "PROD-" in record.product_id
    
    def test_production_record_with_materials(self, auth_service):
        """Test production record with materials"""
        materials = ["Material 1", "Material 2"]
        record = auth_service.create_production_record(
            product_name="Test Product",
            product_category="Test",
            craftsman_name="Test",
            craftsman_contact="+919876543210",
            location="Test",
            materials=materials
        )
        
        assert record.materials_used == materials
    
    def test_production_record_with_techniques(self, auth_service):
        """Test production record with techniques"""
        techniques = ["Technique 1", "Technique 2"]
        record = auth_service.create_production_record(
            product_name="Test Product",
            product_category="Test",
            craftsman_name="Test",
            craftsman_contact="+919876543210",
            location="Test",
            techniques=techniques
        )
        
        assert record.techniques == techniques


class TestDigitalStoryCard:
    """Test Digital Story Card generation"""
    
    @pytest.mark.asyncio
    async def test_generate_story_card_creates_file(self, auth_service, sample_production_record):
        """Test that story card generation creates a PDF file"""
        pdf_doc = await auth_service.generate_digital_story_card(sample_production_record)
        
        assert os.path.exists(pdf_doc.file_path)
        assert pdf_doc.file_path.endswith(".pdf")
    
    @pytest.mark.asyncio
    async def test_story_card_metadata(self, auth_service, sample_production_record):
        """Test story card metadata"""
        pdf_doc = await auth_service.generate_digital_story_card(sample_production_record)
        
        assert pdf_doc.metadata["product_id"] == sample_production_record.product_id
        assert pdf_doc.metadata["product_name"] == sample_production_record.product_name
        assert pdf_doc.metadata["craftsman"] == sample_production_record.craftsman_name
        assert "blockchain_hash" in pdf_doc.metadata
        assert "verification_url" in pdf_doc.metadata
    
    @pytest.mark.asyncio
    async def test_story_card_bilingual(self, auth_service, sample_production_record):
        """Test story card generation in both languages"""
        pdf_hindi = await auth_service.generate_digital_story_card(
            sample_production_record,
            language="hi-IN"
        )
        pdf_english = await auth_service.generate_digital_story_card(
            sample_production_record,
            language="en-IN"
        )
        
        assert os.path.exists(pdf_hindi.file_path)
        assert os.path.exists(pdf_english.file_path)


class TestBlockchainVerification:
    """Test blockchain-based verification"""
    
    @pytest.mark.asyncio
    async def test_blockchain_initialization(self, auth_service):
        """Test blockchain is initialized"""
        assert os.path.exists(auth_service.blockchain_file)
        
        with open(auth_service.blockchain_file, 'r') as f:
            blockchain = json.load(f)
            assert len(blockchain) > 0
            assert blockchain[0]["record_id"] == "genesis"
    
    @pytest.mark.asyncio
    async def test_add_to_blockchain(self, auth_service, sample_production_record):
        """Test adding record to blockchain"""
        # Generate story card (which adds to blockchain)
        pdf_doc = await auth_service.generate_digital_story_card(sample_production_record)
        
        # Load blockchain
        with open(auth_service.blockchain_file, 'r') as f:
            blockchain = json.load(f)
        
        # Verify record was added
        assert len(blockchain) > 1
        
        # Find the product record
        product_records = [
            r for r in blockchain 
            if r.get("data", {}).get("product_id") == sample_production_record.product_id
        ]
        assert len(product_records) > 0
    
    @pytest.mark.asyncio
    async def test_verify_product_authenticity(self, auth_service, sample_production_record):
        """Test product authenticity verification"""
        # Generate story card
        pdf_doc = await auth_service.generate_digital_story_card(sample_production_record)
        
        # Verify authenticity
        verification = auth_service.verify_product_authenticity(sample_production_record.product_id)
        
        assert verification is not None
        assert verification["product_id"] == sample_production_record.product_id
        assert verification["is_authentic"] is True
        assert verification["record_count"] > 0
    
    @pytest.mark.asyncio
    async def test_verify_nonexistent_product(self, auth_service):
        """Test verification of non-existent product"""
        verification = auth_service.verify_product_authenticity("PROD-NONEXISTENT")
        
        assert verification is None
    
    @pytest.mark.asyncio
    async def test_blockchain_integrity(self, auth_service, sample_production_record):
        """Test blockchain integrity verification"""
        # Add multiple records
        pdf1 = await auth_service.generate_digital_story_card(sample_production_record)
        
        record2 = auth_service.create_production_record(
            product_name="Product 2",
            product_category="Test",
            craftsman_name="Craftsman 2",
            craftsman_contact="+919876543211",
            location="Location 2"
        )
        pdf2 = await auth_service.generate_digital_story_card(record2)
        
        # Load and verify blockchain
        with open(auth_service.blockchain_file, 'r') as f:
            blockchain = json.load(f)
        
        is_valid = auth_service._verify_blockchain_integrity(blockchain)
        assert is_valid is True
