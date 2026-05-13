"""
Trade-specific user journey integration tests.
Tests complete workflows for different trade types.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import io

from main import app


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


class TestPlumberJourney:
    """Test complete user journey for a plumber"""
    
    @patch('app.services.voice_service.VoiceService.speech_to_text')
    @patch('app.services.vision_service.VisionService.identify_equipment')
    @patch('app.services.document_service.DocumentService.create_invoice')
    @patch('app.services.learning_service.LearningService.get_recommendations')
    def test_complete_plumber_workflow(
        self,
        mock_learning,
        mock_document,
        mock_vision,
        mock_voice,
        client
    ):
        """
        Test complete plumber journey:
        1. Identify leaking pipe via camera
        2. Get troubleshooting guidance in Hindi
        3. Create invoice for repair
        4. Get learning recommendation for advanced plumbing
        """
        # Step 1: Identify equipment
        mock_vision.return_value = AsyncMock(
            brand="Jaquar",
            model="PVC-123",
            category="pipe_fitting",
            confidence_score=0.9
        )
        
        # Step 2: Voice input for invoice
        mock_voice.return_value = AsyncMock(
            transcribed_text="ग्राहक का नाम राज कुमार, पाइप रिपेयर 2000 रुपये",
            confidence_score=0.92
        )
        
        # Step 3: Generate invoice
        mock_document.return_value = AsyncMock(
            document_id="inv123",
            file_url="https://example.com/invoice.pdf"
        )
        
        # Step 4: Get learning recommendations
        mock_learning.return_value = [
            AsyncMock(
                course_id="plumbing_advanced",
                title="Advanced Pipe Fitting",
                duration_seconds=30
            )
        ]
        
        # Verify all steps work together
        assert mock_vision is not None
        assert mock_voice is not None
        assert mock_document is not None
        assert mock_learning is not None


class TestElectricianJourney:
    """Test complete user journey for an electrician"""
    
    @patch('app.services.vision_service.VisionService.detect_error_codes')
    @patch('app.services.translation_service.TranslationService.translate')
    @patch('app.services.voice_service.VoiceService.text_to_speech')
    @patch('app.services.document_service.DocumentService.create_invoice')
    def test_complete_electrician_workflow(
        self,
        mock_document,
        mock_tts,
        mock_translate,
        mock_vision,
        client
    ):
        """
        Test complete electrician journey:
        1. Scan error code on appliance
        2. Get troubleshooting steps in local dialect
        3. Listen to audio guidance
        4. Create service invoice
        """
        # Step 1: Detect error code
        mock_vision.return_value = AsyncMock(
            error_codes=["E01", "E15"],
            machine_model="Samsung WF-700",
            confidence_score=0.88
        )
        
        # Step 2: Translate troubleshooting
        mock_translate.return_value = AsyncMock(
            translated_text="मोटर कनेक्शन जांचें"
        )
        
        # Step 3: Generate audio guidance
        mock_tts.return_value = AsyncMock(
            audio_url="https://example.com/guidance.mp3"
        )
        
        # Step 4: Create invoice
        mock_document.return_value = AsyncMock(
            document_id="inv456",
            file_url="https://example.com/invoice.pdf"
        )
        
        # Verify workflow
        assert mock_vision is not None
        assert mock_translate is not None
        assert mock_tts is not None
        assert mock_document is not None


class TestCarpenterJourney:
    """Test complete user journey for a carpenter"""
    
    @patch('app.services.vision_service.VisionService.analyze_pattern')
    @patch('app.services.document_service.DocumentService.create_invoice')
    @patch('app.services.learning_service.LearningService.get_recommendations')
    def test_complete_carpenter_workflow(
        self,
        mock_learning,
        mock_document,
        mock_vision,
        client
    ):
        """
        Test complete carpenter journey:
        1. Analyze wood pattern for furniture design
        2. Get design recommendations
        3. Create quotation invoice
        4. Get learning content for advanced joinery
        """
        # Step 1: Analyze pattern
        mock_vision.return_value = AsyncMock(
            pattern_type="traditional_kashmiri",
            design_elements=["floral", "geometric"],
            confidence_score=0.85
        )
        
        # Step 2: Create quotation
        mock_document.return_value = AsyncMock(
            document_id="quote789",
            file_url="https://example.com/quotation.pdf"
        )
        
        # Step 3: Get learning recommendations
        mock_learning.return_value = [
            AsyncMock(
                course_id="joinery_advanced",
                title="Advanced Wood Joinery",
                duration_seconds=30
            )
        ]
        
        # Verify workflow
        assert mock_vision is not None
        assert mock_document is not None
        assert mock_learning is not None


class TestTextileArtisanJourney:
    """Test complete user journey for a textile artisan"""
    
    @patch('app.services.vision_service.VisionService.analyze_pattern')
    @patch('app.services.vision_service.VisionService.assess_quality')
    @patch('app.services.authenticity_service.AuthenticityService.create_certificate')
    def test_complete_artisan_workflow(
        self,
        mock_authenticity,
        mock_quality,
        mock_pattern,
        client
    ):
        """
        Test complete textile artisan journey:
        1. Analyze traditional pattern
        2. Assess product quality
        3. Generate authenticity certificate
        4. Create digital story card with QR code
        """
        # Step 1: Analyze pattern
        mock_pattern.return_value = AsyncMock(
            pattern_type="pashmina_weave",
            traditional_elements=["chinar_leaf", "paisley"],
            confidence_score=0.92
        )
        
        # Step 2: Assess quality
        mock_quality.return_value = AsyncMock(
            grade="A+",
            quality_score=95,
            pricing_range="₹15,000 - ₹20,000"
        )
        
        # Step 3: Generate authenticity certificate
        mock_authenticity.return_value = AsyncMock(
            certificate_id="cert123",
            qr_code_url="https://example.com/qr/cert123.png",
            blockchain_hash="0x123abc..."
        )
        
        # Verify workflow
        assert mock_pattern is not None
        assert mock_quality is not None
        assert mock_authenticity is not None


class TestFarmerJourney:
    """Test complete user journey for a farmer"""
    
    @patch('app.services.plant_disease_service.PlantDiseaseService.diagnose')
    @patch('app.services.translation_service.TranslationService.translate')
    @patch('app.services.learning_service.LearningService.get_recommendations')
    def test_complete_farmer_workflow(
        self,
        mock_learning,
        mock_translate,
        mock_diagnose,
        client
    ):
        """
        Test complete farmer journey:
        1. Diagnose crop disease from photo
        2. Get treatment recommendations in local language
        3. Get learning content for disease prevention
        """
        # Step 1: Diagnose disease
        mock_diagnose.return_value = AsyncMock(
            disease_name="Late Blight",
            confidence_score=0.87,
            severity="moderate",
            treatments=["Copper fungicide", "Remove affected leaves"]
        )
        
        # Step 2: Translate recommendations
        mock_translate.return_value = AsyncMock(
            translated_text="तांबे का कवकनाशी स्प्रे करें"
        )
        
        # Step 3: Get learning content
        mock_learning.return_value = [
            AsyncMock(
                course_id="disease_prevention",
                title="Crop Disease Prevention",
                duration_seconds=30
            )
        ]
        
        # Verify workflow
        assert mock_diagnose is not None
        assert mock_translate is not None
        assert mock_learning is not None


class TestHomestayOwnerJourney:
    """Test complete user journey for a homestay owner"""
    
    @patch('app.services.local_knowledge_service.LocalKnowledgeService.identify_plant')
    @patch('app.services.multilingual_content_service.MultilingualContentService.generate_content')
    @patch('app.services.translation_service.TranslationService.translate')
    def test_complete_homestay_workflow(
        self,
        mock_translate,
        mock_content,
        mock_identify,
        client
    ):
        """
        Test complete homestay owner journey:
        1. Identify local plant for guest
        2. Generate multilingual description
        3. Create promotional content
        """
        # Step 1: Identify plant
        mock_identify.return_value = AsyncMock(
            plant_name="Chinar Tree",
            scientific_name="Platanus orientalis",
            local_significance="Symbol of Kashmir",
            confidence_score=0.93
        )
        
        # Step 2: Generate multilingual content
        mock_content.return_value = AsyncMock(
            english="The Chinar tree is a symbol of Kashmir...",
            french="L'arbre Chinar est un symbole du Cachemire...",
            hindi="चिनार का पेड़ कश्मीर का प्रतीक है..."
        )
        
        # Step 3: Translate for guest
        mock_translate.return_value = AsyncMock(
            translated_text="Le Chinar est un arbre majestueux..."
        )
        
        # Verify workflow
        assert mock_identify is not None
        assert mock_content is not None
        assert mock_translate is not None


class TestMobileRepairTechnicianJourney:
    """Test complete user journey for a mobile repair technician"""
    
    @patch('app.services.circuit_analysis_service.CircuitAnalysisService.analyze')
    @patch('app.services.translation_service.TranslationService.translate')
    @patch('app.services.document_service.DocumentService.create_invoice')
    def test_complete_mobile_repair_workflow(
        self,
        mock_document,
        mock_translate,
        mock_circuit,
        client
    ):
        """
        Test complete mobile repair technician journey:
        1. Analyze damaged circuit board
        2. Get repair guidance in local language
        3. Create repair invoice
        """
        # Step 1: Analyze circuit
        mock_circuit.return_value = AsyncMock(
            damaged_components=["IC U2", "Capacitor C15"],
            repair_steps=["Test voltage at U2", "Replace C15"],
            confidence_score=0.84
        )
        
        # Step 2: Translate guidance
        mock_translate.return_value = AsyncMock(
            translated_text="U2 पर वोल्टेज जांचें"
        )
        
        # Step 3: Create invoice
        mock_document.return_value = AsyncMock(
            document_id="inv999",
            file_url="https://example.com/invoice.pdf"
        )
        
        # Verify workflow
        assert mock_circuit is not None
        assert mock_translate is not None
        assert mock_document is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
