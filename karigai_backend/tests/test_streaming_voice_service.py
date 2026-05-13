"""
Unit tests for Streaming Voice Service
"""

import pytest
import asyncio
from datetime import datetime
from app.services.streaming_voice_service import (
    StreamingVoiceService,
    VoiceActivityState,
    PartialResult,
    ConversationContext
)


@pytest.fixture
def streaming_service():
    """Create a streaming voice service instance"""
    return StreamingVoiceService(latency_target_ms=500)


class TestStreamingVoiceService:
    """Test suite for Streaming Voice Service"""
    
    @pytest.mark.asyncio
    async def test_start_streaming_session(self, streaming_service):
        """Test starting a streaming session"""
        context = await streaming_service.start_streaming_session(
            session_id="session1",
            user_id="user1",
            language="en-IN"
        )
        
        assert context.session_id == "session1"
        assert context.user_id == "user1"
        assert context.language == "en-IN"
        assert len(context.conversation_history) == 0
        assert context.current_topic is None
    
    @pytest.mark.asyncio
    async def test_process_audio_chunk(self, streaming_service):
        """Test processing audio chunk"""
        # Create session
        active_session = await streaming_service.start_streaming_session(
            "test_session_1", "user123", "hi-IN"
        )
        
        # Create audio chunk with sufficient data
        audio_chunk = bytes([128 + i % 50 for i in range(200)])
        
        result = await streaming_service.process_audio_chunk(
            active_session.session_id,
            audio_chunk
        )
        
        assert result is not None
        assert isinstance(result, PartialResult)
        assert result.language == "hi-IN"
        assert not result.is_final
    
    @pytest.mark.asyncio
    async def test_process_audio_chunk_with_callback(self, streaming_service):
        """Test processing audio chunk with callback"""
        active_session = await streaming_service.start_streaming_session(
            "test_session_2", "user123", "hi-IN"
        )
        
        callback_called = False
        callback_result = None
        
        def callback(result):
            nonlocal callback_called, callback_result
            callback_called = True
            callback_result = result
        
        audio_chunk = bytes([128 + i % 50 for i in range(200)])
        
        result = await streaming_service.process_audio_chunk(
            active_session.session_id,
            audio_chunk,
            callback=callback
        )
        
        assert callback_called
        assert callback_result == result
    
    @pytest.mark.asyncio
    async def test_process_audio_chunk_invalid_session(self, streaming_service):
        """Test processing audio chunk with invalid session"""
        audio_chunk = bytes([128] * 200)
        
        with pytest.raises(ValueError, match="Session .* not found"):
            await streaming_service.process_audio_chunk(
                "invalid_session",
                audio_chunk
            )
    
    @pytest.mark.asyncio
    async def test_voice_activity_detection_speech(self, streaming_service):
        """Test voice activity detection for speech"""
        # High energy audio (speech)
        audio_chunk = bytes([200] * 100)
        
        vad_state = streaming_service._detect_voice_activity(audio_chunk)
        
        assert vad_state == VoiceActivityState.SPEECH
    
    @pytest.mark.asyncio
    async def test_voice_activity_detection_silence(self, streaming_service):
        """Test voice activity detection for silence"""
        # Low energy audio (silence)
        audio_chunk = bytes([128] * 100)
        
        vad_state = streaming_service._detect_voice_activity(audio_chunk)
        
        assert vad_state == VoiceActivityState.SILENCE
    
    @pytest.mark.asyncio
    async def test_voice_activity_detection_empty(self, streaming_service):
        """Test voice activity detection for empty audio"""
        audio_chunk = bytes()
        
        vad_state = streaming_service._detect_voice_activity(audio_chunk)
        
        assert vad_state == VoiceActivityState.SILENCE
    
    @pytest.mark.asyncio
    async def test_get_conversation_context(self, streaming_service):
        """Test getting conversation context"""
        active_session = await streaming_service.start_streaming_session(
            "test_session_3", "user123", "hi-IN"
        )
        
        context = streaming_service.get_conversation_context(active_session.session_id)
        
        assert context is not None
        assert context.session_id == active_session.session_id
        assert context.user_id == active_session.user_id
    
    @pytest.mark.asyncio
    async def test_get_conversation_context_invalid_session(self, streaming_service):
        """Test getting conversation context for invalid session"""
        context = streaming_service.get_conversation_context("invalid_session")
        
        assert context is None
    
    @pytest.mark.asyncio
    async def test_update_conversation_context(self, streaming_service):
        """Test updating conversation context"""
        active_session = await streaming_service.start_streaming_session(
            "test_session_4", "user123", "hi-IN"
        )
        
        streaming_service.update_conversation_context(
            active_session.session_id,
            "How do I fix a leak?",
            "First, turn off the water supply."
        )
        
        context = streaming_service.get_conversation_context(active_session.session_id)
        
        assert len(context.conversation_history) == 2
        assert context.conversation_history[0]["role"] == "user"
        assert context.conversation_history[1]["role"] == "assistant"
        assert context.current_topic is not None
    
    @pytest.mark.asyncio
    async def test_get_context_for_response(self, streaming_service):
        """Test getting context for response generation"""
        active_session = await streaming_service.start_streaming_session(
            "test_session_5", "user123", "hi-IN"
        )
        
        # Add some conversation history
        for i in range(5):
            streaming_service.update_conversation_context(
                active_session.session_id,
                f"Question {i}",
                f"Answer {i}"
            )
        
        context_messages = streaming_service.get_context_for_response(active_session.session_id)
        
        assert len(context_messages) == 10  # 5 exchanges = 10 messages
    
    @pytest.mark.asyncio
    async def test_get_context_for_response_limits_history(self, streaming_service):
        """Test that context for response limits history to recent messages"""
        active_session = await streaming_service.start_streaming_session(
            "test_session_6", "user123", "hi-IN"
        )
        
        # Add many conversation exchanges
        for i in range(15):
            streaming_service.update_conversation_context(
                active_session.session_id,
                f"Question {i}",
                f"Answer {i}"
            )
        
        context_messages = streaming_service.get_context_for_response(active_session.session_id)
        
        # Should return only last 20 messages (10 exchanges)
        assert len(context_messages) == 20
    
    @pytest.mark.asyncio
    async def test_end_streaming_session(self, streaming_service):
        """Test ending a streaming session"""
        active_session = await streaming_service.start_streaming_session(
            "test_session_7", "user123", "hi-IN"
        )
        
        # Add some activity
        streaming_service.update_conversation_context(
            active_session.session_id,
            "Test message",
            "Test response"
        )
        
        summary = await streaming_service.end_streaming_session(active_session.session_id)
        
        assert summary["session_id"] == active_session.session_id
        assert summary["user_id"] == active_session.user_id
        assert summary["total_exchanges"] == 1
        assert summary["language"] == "hi-IN"
        assert "duration_seconds" in summary
        
        # Session should be removed
        context = streaming_service.get_conversation_context(active_session.session_id)
        assert context is None
    
    @pytest.mark.asyncio
    async def test_end_streaming_session_invalid(self, streaming_service):
        """Test ending an invalid session"""
        summary = await streaming_service.end_streaming_session("invalid_session")
        
        assert "error" in summary
    
    @pytest.mark.asyncio
    async def test_stream_transcription(self, streaming_service):
        """Test streaming transcription"""
        active_session = await streaming_service.start_streaming_session(
            "test_session_8", "user123", "hi-IN"
        )
        
        # Create async generator for audio stream
        async def audio_stream():
            for i in range(3):
                yield bytes([128 + i * 10] * 200)
                await asyncio.sleep(0.01)
        
        results = []
        async for result in streaming_service.stream_transcription(
            active_session.session_id,
            audio_stream()
        ):
            results.append(result)
        
        assert len(results) > 0
        for result in results:
            assert isinstance(result, PartialResult)
    
    @pytest.mark.asyncio
    async def test_finalize_pending_results(self, streaming_service):
        """Test finalizing pending results"""
        active_session = await streaming_service.start_streaming_session(
            "test_session_9", "user123", "hi-IN"
        )
        
        # Add some partial results
        audio_chunk = bytes([150] * 200)
        await streaming_service.process_audio_chunk(active_session.session_id, audio_chunk)
        await streaming_service.process_audio_chunk(active_session.session_id, audio_chunk)
        
        # Finalize
        final_result = await streaming_service._finalize_pending_results(active_session.session_id)
        
        assert final_result is not None
        assert final_result.is_final
        assert len(final_result.text) > 0
    
    @pytest.mark.asyncio
    async def test_extract_topic(self, streaming_service):
        """Test topic extraction"""
        topic = streaming_service._extract_topic("I need help to repair my pipe")
        
        assert topic in ["help", "repair"]
    
    @pytest.mark.asyncio
    async def test_extract_topic_no_match(self, streaming_service):
        """Test topic extraction with no match"""
        topic = streaming_service._extract_topic("Hello there")
        
        assert topic is None
    
    @pytest.mark.asyncio
    async def test_get_active_sessions_count(self, streaming_service):
        """Test getting active sessions count"""
        initial_count = streaming_service.get_active_sessions_count()
        
        await streaming_service.start_streaming_session("session1", "user1")
        await streaming_service.start_streaming_session("session2", "user2")
        
        assert streaming_service.get_active_sessions_count() == initial_count + 2
    
    @pytest.mark.asyncio
    async def test_cleanup_inactive_sessions(self, streaming_service):
        """Test cleanup of inactive sessions"""
        # Create a session
        context = await streaming_service.start_streaming_session("session1", "user1")
        
        # Manually set last activity to old time
        from datetime import timedelta
        context.last_activity = datetime.now() - timedelta(minutes=35)
        
        # Cleanup with 30 minute timeout
        cleaned = streaming_service.cleanup_inactive_sessions(timeout_minutes=30)
        
        assert cleaned == 1
        assert streaming_service.get_conversation_context("session1") is None
    
    @pytest.mark.asyncio
    async def test_latency_target(self, streaming_service):
        """Test that latency target is set"""
        assert streaming_service.latency_target_ms == 500
    
    @pytest.mark.asyncio
    async def test_partial_result_confidence_increases(self, streaming_service):
        """Test that confidence increases with more audio"""
        active_session = await streaming_service.start_streaming_session(
            "test_session_10", "user123", "hi-IN"
        )
        
        # Small chunk
        small_chunk = bytes([150] * 150)
        result1 = await streaming_service.process_audio_chunk(
            active_session.session_id,
            small_chunk
        )
        
        # Clear buffer
        streaming_service.partial_results_buffer[active_session.session_id] = []
        
        # Larger chunk
        large_chunk = bytes([150] * 500)
        result2 = await streaming_service.process_audio_chunk(
            active_session.session_id,
            large_chunk
        )
        
        if result1 and result2:
            assert result2.confidence >= result1.confidence
