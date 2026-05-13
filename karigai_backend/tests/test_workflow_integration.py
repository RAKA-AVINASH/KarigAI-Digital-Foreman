"""
Comprehensive integration tests for end-to-end workflows.
Tests complete user journeys across multiple services.
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import io
from PIL import Image

from main import app
from app.core.database import get_db


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def mock_audio_file():
    """Mock audio file for testing"""
    audio_data = b"fake audio data"
    return ("test_audio.wav", io.BytesIO(audio_data), "audio/wav")


@pytest.fixture
def mock_image_file():
    """Mock image file for testing"""
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return ("test_image.png", img_bytes, "image/png")


class TestVoiceToInvoiceWorkflow:
    """Test complete voice-to-invoice workflow"""
    
    @patch('app.services.voice_service.VoiceService.speech_to_text')
    @patch('app.services.document_service.DocumentService.create_invoice')
    @patch('app.services.whatsapp_service.WhatsAppService.send_document')
    def test_complete_workflow_success(
        self, 
        mock_whatsapp, 
        mock_create_invoice, 
        mock_stt,
        client,
        mock_audio_file
    ):
        """Test successful voice-to-invoice workflow"""
        # Mock voice recognition
        mock_stt.return_value = AsyncMock(
            transcribed_text="Customer name John, amount 5000 rupees",
            confidence_score=0.95
        )
        
        # Mock document generation
        mock_create_invoice.return_value = AsyncMock(
            document_id="doc123",
            file_url="https://example.com/invoice.pdf"
        )
        
        # Mock WhatsApp sending
        mock_whatsapp.return_value = AsyncMock(success=True)
        
        # Make request
        response = client.post(
            "/api/v1/workflows/voice-to-invoice",
            files={"audio_file": mock_audio_file},
            data={
                "user_id": "user123",
                "language_code": "hi-IN",
                "customer_phone": "+919876543210"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "transcribed_text" in data
        assert "invoice_id" in data
        assert "document_url" in data
        assert data["whatsapp_sent"] == True
        assert data["confidence_score"] >= 0.8
    
    @patch('app.services.voice_service.VoiceService.speech_to_text')
    def test_low_confidence_handling(self, mock_stt, client, mock_audio_file):
        """Test workflow handles low confidence voice recognition"""
        # Mock low confidence recognition
        mock_stt.return_value = AsyncMock(
            transcribed_text="unclear audio",
            confidence_score=0.5
        )
        
        response = client.post(
            "/api/v1/workflows/voice-to-invoice",
            files={"audio_file": mock_audio_file},
            data={"user_id": "user123", "language_code": "hi-IN"}
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "user_message" in data
        assert "confidence" in data.get("details", {})


class TestEquipmentTroubleshootingWorkflow:
    """Test complete equipment troubleshooting workflow"""
    
    @patch('app.services.vision_service.VisionService.identify_equipment')
    @patch('app.services.translation_service.TranslationService.translate')
    @patch('app.services.voice_service.VoiceService.text_to_speech')
    def test_complete_workflow_success(
        self,
        mock_tts,
        mock_translate,
        mock_identify,
        client,
        mock_image_file
    ):
        """Test successful equipment troubleshooting workflow"""
        # Mock equipment identification
        mock_identify.return_value = AsyncMock(
            brand="Samsung",
            model="WF-123",
            category="washing_machine",
            confidence_score=0.9
        )
        
        # Mock translation
        mock_translate.return_value = AsyncMock(
            translated_text="बिजली कनेक्शन जांचें"
        )
        
        # Mock TTS
        mock_tts.return_value = AsyncMock(
            audio_url="https://example.com/guidance.mp3"
        )
        
        response = client.post(
            "/api/v1/workflows/equipment-troubleshooting",
            files={"image_file": mock_image_file},
            data={"user_id": "user123", "language_code": "hi-IN"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "equipment_info" in data
        assert "troubleshooting_steps" in data
        assert "audio_guidance_url" in data
        assert data["confidence_score"] >= 0.7
    
    @patch('app.services.vision_service.VisionService.identify_equipment')
    def test_unrecognizable_equipment(self, mock_identify, client, mock_image_file):
        """Test workflow handles unrecognizable equipment"""
        # Mock low confidence identification
        mock_identify.return_value = AsyncMock(
            brand="Unknown",
            model="Unknown",
            category="unknown",
            confidence_score=0.3
        )
        
        response = client.post(
            "/api/v1/workflows/equipment-troubleshooting",
            files={"image_file": mock_image_file},
            data={"user_id": "user123", "language_code": "hi-IN"}
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "user_message" in data


class TestLearningRecommendationWorkflow:
    """Test complete learning recommendation workflow"""
    
    @patch('app.services.learning_service.LearningService.get_recommendations')
    @patch('app.core.offline_manager.OfflineManager.prepare_offline_content')
    @patch('app.services.user_service.UserService.log_activity')
    def test_complete_workflow_success(
        self,
        mock_log,
        mock_offline,
        mock_recommendations,
        client
    ):
        """Test successful learning recommendation workflow"""
        # Mock recommendations
        mock_recommendations.return_value = [
            AsyncMock(
                course_id="course1",
                title="Basic Plumbing",
                duration_seconds=30
            ),
            AsyncMock(
                course_id="course2",
                title="Advanced Repairs",
                duration_seconds=30
            )
        ]
        
        # Mock offline preparation
        mock_offline.return_value = AsyncMock(
            content_id="course1",
            size_bytes=1024000,
            ready=True
        )
        
        # Mock activity logging
        mock_log.return_value = AsyncMock(success=True)
        
        response = client.post(
            "/api/v1/workflows/learning-recommendation",
            json={
                "user_id": "user123",
                "query_history": ["how to fix leak", "pipe repair"],
                "language_code": "hi-IN"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data
        assert "offline_ready" in data
        assert "total_count" in data
        assert len(data["recommendations"]) > 0


class TestOfflineDataSyncWorkflow:
    """Test complete offline data sync workflow"""
    
    @patch('app.services.sync_service.SyncService.validate_offline_data')
    @patch('app.services.sync_service.SyncService.sync_user_data')
    @patch('app.services.storage_manager.StorageManager.update_usage_patterns')
    def test_complete_workflow_success(
        self,
        mock_storage,
        mock_sync,
        mock_validate,
        client
    ):
        """Test successful offline data sync workflow"""
        # Mock validation
        mock_validate.return_value = AsyncMock(
            is_valid=True,
            errors=[]
        )
        
        # Mock sync
        mock_sync.return_value = AsyncMock(
            synced_count=10,
            conflicts_resolved=2,
            failed_items=[],
            synced_items=["item1", "item2"]
        )
        
        # Mock storage update
        mock_storage.return_value = AsyncMock(success=True)
        
        offline_data = {
            "documents": [{"id": "doc1", "data": "test"}],
            "progress": [{"course_id": "course1", "completion": 50}]
        }
        
        response = client.post(
            "/api/v1/workflows/sync-offline-data",
            params={"user_id": "user123"},
            json=offline_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "synced_count" in data
        assert "conflicts_resolved" in data
        assert "failed_items" in data
        assert data["synced_count"] > 0
    
    @patch('app.services.sync_service.SyncService.validate_offline_data')
    def test_invalid_offline_data(self, mock_validate, client):
        """Test workflow handles invalid offline data"""
        # Mock validation failure
        mock_validate.return_value = AsyncMock(
            is_valid=False,
            errors=["Invalid timestamp", "Missing required field"]
        )
        
        offline_data = {"invalid": "data"}
        
        response = client.post(
            "/api/v1/workflows/sync-offline-data",
            params={"user_id": "user123"},
            json=offline_data
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


class TestMultiLanguageWorkflows:
    """Test workflows with multiple languages"""
    
    @pytest.mark.parametrize("language_code", [
        "hi-IN",  # Hindi
        "ml-IN",  # Malayalam
        "en-US",  # English
        "pa-IN",  # Punjabi
    ])
    @patch('app.services.voice_service.VoiceService.speech_to_text')
    @patch('app.services.document_service.DocumentService.create_invoice')
    def test_voice_to_invoice_multiple_languages(
        self,
        mock_create_invoice,
        mock_stt,
        language_code,
        client,
        mock_audio_file
    ):
        """Test voice-to-invoice workflow with different languages"""
        mock_stt.return_value = AsyncMock(
            transcribed_text="Test transcription",
            confidence_score=0.9
        )
        
        mock_create_invoice.return_value = AsyncMock(
            document_id="doc123",
            file_url="https://example.com/invoice.pdf"
        )
        
        response = client.post(
            "/api/v1/workflows/voice-to-invoice",
            files={"audio_file": mock_audio_file},
            data={
                "user_id": "user123",
                "language_code": language_code
            }
        )
        
        assert response.status_code == 200


class TestPerformanceUnderLoad:
    """Test workflow performance under various load conditions"""
    
    @pytest.mark.asyncio
    @patch('app.services.voice_service.VoiceService.speech_to_text')
    @patch('app.services.document_service.DocumentService.create_invoice')
    async def test_concurrent_voice_to_invoice_requests(
        self,
        mock_create_invoice,
        mock_stt,
        client,
        mock_audio_file
    ):
        """Test multiple concurrent voice-to-invoice requests"""
        mock_stt.return_value = AsyncMock(
            transcribed_text="Test",
            confidence_score=0.9
        )
        
        mock_create_invoice.return_value = AsyncMock(
            document_id="doc123",
            file_url="https://example.com/invoice.pdf"
        )
        
        # Simulate 10 concurrent requests
        tasks = []
        for i in range(10):
            task = asyncio.create_task(
                asyncio.to_thread(
                    client.post,
                    "/api/v1/workflows/voice-to-invoice",
                    files={"audio_file": mock_audio_file},
                    data={"user_id": f"user{i}", "language_code": "hi-IN"}
                )
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
