"""
Streaming Voice Processing Service

This service provides real-time voice transcription with partial results,
conversation context maintenance, and low-latency processing.
"""

from typing import Optional, List, Dict, Callable, AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import asyncio


class VoiceActivityState(Enum):
    """Voice activity detection states"""
    SILENCE = "silence"
    SPEECH = "speech"
    UNKNOWN = "unknown"


@dataclass
class PartialResult:
    """Partial transcription result"""
    text: str
    confidence: float
    is_final: bool
    timestamp: datetime
    language: str


@dataclass
class ConversationContext:
    """Conversation context for maintaining state"""
    session_id: str
    user_id: str
    conversation_history: List[Dict[str, str]]
    current_topic: Optional[str]
    language: str
    started_at: datetime
    last_activity: datetime


class StreamingVoiceService:
    """
    Service for streaming voice processing
    
    Provides:
    - Real-time transcription with partial results
    - Immediate feedback during speech
    - Conversation context maintenance
    - Low-latency voice processing pipeline
    - Voice activity detection and silence handling
    """
    
    def __init__(self, latency_target_ms: int = 500):
        """
        Initialize streaming voice service
        
        Args:
            latency_target_ms: Target latency in milliseconds
        """
        self.latency_target_ms = latency_target_ms
        self.active_sessions: Dict[str, ConversationContext] = {}
        self.partial_results_buffer: Dict[str, List[PartialResult]] = {}
        self.vad_threshold = 0.5  # Voice activity detection threshold
        
    async def start_streaming_session(
        self,
        session_id: str,
        user_id: str,
        language: str = "hi-IN"
    ) -> ConversationContext:
        """
        Start a new streaming session
        
        Args:
            session_id: Unique session identifier
            user_id: User identifier
            language: Language code
            
        Returns:
            ConversationContext for the session
        """
        context = ConversationContext(
            session_id=session_id,
            user_id=user_id,
            conversation_history=[],
            current_topic=None,
            language=language,
            started_at=datetime.now(),
            last_activity=datetime.now()
        )
        
        self.active_sessions[session_id] = context
        self.partial_results_buffer[session_id] = []
        
        return context
    
    async def process_audio_chunk(
        self,
        session_id: str,
        audio_chunk: bytes,
        callback: Optional[Callable[[PartialResult], None]] = None
    ) -> Optional[PartialResult]:
        """
        Process an audio chunk and return partial result
        
        Args:
            session_id: Session identifier
            audio_chunk: Audio data chunk
            callback: Optional callback for immediate feedback
            
        Returns:
            PartialResult if transcription available
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        context = self.active_sessions[session_id]
        
        # Detect voice activity
        vad_state = self._detect_voice_activity(audio_chunk)
        
        if vad_state == VoiceActivityState.SILENCE:
            # Handle silence - finalize any pending results
            return await self._finalize_pending_results(session_id)
        
        # Process audio chunk for transcription
        partial_result = await self._transcribe_chunk(
            audio_chunk,
            context.language,
            session_id
        )
        
        if partial_result:
            # Store in buffer
            self.partial_results_buffer[session_id].append(partial_result)
            
            # Update context
            context.last_activity = datetime.now()
            
            # Immediate callback for low latency
            if callback:
                callback(partial_result)
            
            return partial_result
        
        return None
    
    async def stream_transcription(
        self,
        session_id: str,
        audio_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[PartialResult]:
        """
        Stream transcription results as audio arrives
        
        Args:
            session_id: Session identifier
            audio_stream: Async iterator of audio chunks
            
        Yields:
            PartialResult objects as they become available
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        async for audio_chunk in audio_stream:
            result = await self.process_audio_chunk(session_id, audio_chunk)
            if result:
                yield result
    
    def get_conversation_context(self, session_id: str) -> Optional[ConversationContext]:
        """Get conversation context for a session"""
        return self.active_sessions.get(session_id)
    
    def update_conversation_context(
        self,
        session_id: str,
        user_message: str,
        assistant_response: str
    ) -> None:
        """
        Update conversation context with new exchange
        
        Args:
            session_id: Session identifier
            user_message: User's message
            assistant_response: Assistant's response
        """
        if session_id not in self.active_sessions:
            return
        
        context = self.active_sessions[session_id]
        
        # Add to conversation history
        context.conversation_history.append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })
        context.conversation_history.append({
            "role": "assistant",
            "content": assistant_response,
            "timestamp": datetime.now().isoformat()
        })
        
        # Update topic if needed
        context.current_topic = self._extract_topic(user_message)
        context.last_activity = datetime.now()
    
    def get_context_for_response(self, session_id: str) -> List[Dict[str, str]]:
        """
        Get conversation context for generating response
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of conversation messages
        """
        if session_id not in self.active_sessions:
            return []
        
        context = self.active_sessions[session_id]
        
        # Return recent conversation history (last 10 exchanges)
        return context.conversation_history[-20:]  # 10 exchanges = 20 messages
    
    async def end_streaming_session(self, session_id: str) -> Dict[str, any]:
        """
        End a streaming session and return summary
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session summary
        """
        if session_id not in self.active_sessions:
            return {"error": "Session not found"}
        
        context = self.active_sessions[session_id]
        
        # Finalize any pending results
        await self._finalize_pending_results(session_id)
        
        # Create summary
        summary = {
            "session_id": session_id,
            "user_id": context.user_id,
            "duration_seconds": (datetime.now() - context.started_at).total_seconds(),
            "total_exchanges": len(context.conversation_history) // 2,
            "language": context.language,
            "final_topic": context.current_topic
        }
        
        # Cleanup
        del self.active_sessions[session_id]
        if session_id in self.partial_results_buffer:
            del self.partial_results_buffer[session_id]
        
        return summary
    
    def _detect_voice_activity(self, audio_chunk: bytes) -> VoiceActivityState:
        """
        Detect voice activity in audio chunk
        
        Args:
            audio_chunk: Audio data
            
        Returns:
            VoiceActivityState
        """
        # Simplified VAD - in production, use WebRTC VAD or similar
        if len(audio_chunk) == 0:
            return VoiceActivityState.SILENCE
        
        # Calculate simple energy level
        energy = sum(abs(b - 128) for b in audio_chunk) / len(audio_chunk)
        
        # Lower threshold for testing (10% of max energy)
        if energy > 10:
            return VoiceActivityState.SPEECH
        else:
            return VoiceActivityState.SILENCE
    
    async def _transcribe_chunk(
        self,
        audio_chunk: bytes,
        language: str,
        session_id: str
    ) -> Optional[PartialResult]:
        """
        Transcribe audio chunk
        
        Args:
            audio_chunk: Audio data
            language: Language code
            session_id: Session identifier
            
        Returns:
            PartialResult if transcription available
        """
        # Simulate transcription (in production, use Whisper API or similar)
        # This would be replaced with actual streaming ASR
        
        # Simulate processing delay
        await asyncio.sleep(0.1)  # 100ms latency
        
        # Get previous partial results for context
        previous_results = self.partial_results_buffer.get(session_id, [])
        
        # Simulate partial transcription
        if len(audio_chunk) > 100:
            text = f"[Partial transcription {len(previous_results) + 1}]"
            confidence = 0.7 + (len(audio_chunk) / 10000) * 0.2  # Increases with more audio
            
            return PartialResult(
                text=text,
                confidence=min(confidence, 0.95),
                is_final=False,
                timestamp=datetime.now(),
                language=language
            )
        
        return None
    
    async def _finalize_pending_results(self, session_id: str) -> Optional[PartialResult]:
        """
        Finalize pending partial results
        
        Args:
            session_id: Session identifier
            
        Returns:
            Final PartialResult if available
        """
        if session_id not in self.partial_results_buffer:
            return None
        
        partial_results = self.partial_results_buffer[session_id]
        
        if not partial_results:
            return None
        
        # Combine partial results into final result
        combined_text = " ".join([r.text for r in partial_results])
        avg_confidence = sum(r.confidence for r in partial_results) / len(partial_results)
        
        final_result = PartialResult(
            text=combined_text,
            confidence=avg_confidence,
            is_final=True,
            timestamp=datetime.now(),
            language=partial_results[0].language
        )
        
        # Clear buffer
        self.partial_results_buffer[session_id] = []
        
        return final_result
    
    def _extract_topic(self, text: str) -> Optional[str]:
        """
        Extract topic from text
        
        Args:
            text: Input text
            
        Returns:
            Extracted topic or None
        """
        # Simplified topic extraction (in production, use NLP)
        keywords = ["repair", "fix", "install", "price", "cost", "help"]
        
        text_lower = text.lower()
        for keyword in keywords:
            if keyword in text_lower:
                return keyword
        
        return None
    
    def get_active_sessions_count(self) -> int:
        """Get count of active sessions"""
        return len(self.active_sessions)
    
    def cleanup_inactive_sessions(self, timeout_minutes: int = 30) -> int:
        """
        Cleanup inactive sessions
        
        Args:
            timeout_minutes: Timeout in minutes
            
        Returns:
            Number of sessions cleaned up
        """
        now = datetime.now()
        inactive_sessions = []
        
        for session_id, context in self.active_sessions.items():
            inactive_duration = (now - context.last_activity).total_seconds() / 60
            if inactive_duration > timeout_minutes:
                inactive_sessions.append(session_id)
        
        # Remove inactive sessions
        for session_id in inactive_sessions:
            del self.active_sessions[session_id]
            if session_id in self.partial_results_buffer:
                del self.partial_results_buffer[session_id]
        
        return len(inactive_sessions)
