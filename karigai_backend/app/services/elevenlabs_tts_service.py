"""
ElevenLabs Text-to-Speech Service

This module implements the ElevenLabs TTS service for natural voice synthesis
with support for multiple Indian languages and accents, including voice caching
for frequently used phrases.
"""

import asyncio
import hashlib
import json
import os
import time
from typing import Dict, List, Optional, Any
import aiohttp
import aiofiles
from dataclasses import dataclass, asdict

from app.core.voice_engine import AudioData, VoiceProcessingError
from app.core.config_ai_services import AIServicesConfig


@dataclass
class VoiceSettings:
    """ElevenLabs voice configuration settings."""
    stability: float = 0.75
    similarity_boost: float = 0.75
    style: float = 0.0
    use_speaker_boost: bool = True


@dataclass
class CachedVoiceEntry:
    """Cached voice synthesis entry."""
    text: str
    language_code: str
    voice_id: str
    voice_settings: VoiceSettings
    audio_data: AudioData
    created_at: float
    access_count: int = 0
    last_accessed: float = 0.0


class ElevenLabsTTSService:
    """
    ElevenLabs Text-to-Speech service implementation.
    
    Provides natural voice synthesis with support for multiple Indian languages
    and accents, including intelligent voice caching for performance optimization.
    """
    
    def __init__(self, config: AIServicesConfig):
        self.config = config
        self.api_key = config.elevenlabs_api_key
        self.base_url = "https://api.elevenlabs.io/v1"
        
        # Voice cache configuration
        self.cache_dir = "cache/voice"
        self.max_cache_size = 100  # Maximum cached entries
        self.cache_ttl = 7 * 24 * 3600  # 7 days in seconds
        self.voice_cache: Dict[str, CachedVoiceEntry] = {}
        
        # Language to voice mapping for Indian languages
        self.language_voice_mapping = {
            "hi-IN": "pNInz6obpgDQGcFmaJgB",  # Hindi voice
            "en-IN": "21m00Tcm4TlvDq8ikWAM",  # English (Indian accent)
            "en-US": "21m00Tcm4TlvDq8ikWAM",  # English (US)
            "ml-IN": "pNInz6obpgDQGcFmaJgB",  # Malayalam (fallback to Hindi voice)
            "pa-IN": "pNInz6obpgDQGcFmaJgB",  # Punjabi (fallback to Hindi voice)
            "bn-IN": "pNInz6obpgDQGcFmaJgB",  # Bengali (fallback to Hindi voice)
            "ta-IN": "pNInz6obpgDQGcFmaJgB",  # Tamil (fallback to Hindi voice)
            "te-IN": "pNInz6obpgDQGcFmaJgB",  # Telugu (fallback to Hindi voice)
        }
        
        # Default voice settings for different languages
        self.default_voice_settings = {
            "hi-IN": VoiceSettings(stability=0.8, similarity_boost=0.8, style=0.2),
            "en-IN": VoiceSettings(stability=0.75, similarity_boost=0.75, style=0.1),
            "en-US": VoiceSettings(stability=0.7, similarity_boost=0.7, style=0.0),
        }
        
        # Initialize cache directory
        self._initialize_cache()
        
        # Load existing cache
        asyncio.create_task(self._load_cache())
    
    def _initialize_cache(self):
        """Initialize voice cache directory."""
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(f"{self.cache_dir}/audio", exist_ok=True)
        os.makedirs(f"{self.cache_dir}/metadata", exist_ok=True)
    
    async def _load_cache(self):
        """Load existing voice cache from disk."""
        try:
            cache_index_path = f"{self.cache_dir}/cache_index.json"
            if os.path.exists(cache_index_path):
                async with aiofiles.open(cache_index_path, 'r') as f:
                    cache_data = json.loads(await f.read())
                
                for cache_key, entry_data in cache_data.items():
                    # Load audio data
                    audio_path = f"{self.cache_dir}/audio/{cache_key}.wav"
                    if os.path.exists(audio_path):
                        async with aiofiles.open(audio_path, 'rb') as f:
                            audio_bytes = await f.read()
                        
                        # Reconstruct AudioData
                        audio_data = AudioData(
                            audio_bytes=audio_bytes,
                            sample_rate=entry_data['sample_rate'],
                            channels=entry_data['channels'],
                            duration=entry_data['duration'],
                            format=entry_data['format'],
                            bit_depth=entry_data['bit_depth']
                        )
                        
                        # Reconstruct VoiceSettings
                        voice_settings = VoiceSettings(**entry_data['voice_settings'])
                        
                        # Create cache entry
                        cache_entry = CachedVoiceEntry(
                            text=entry_data['text'],
                            language_code=entry_data['language_code'],
                            voice_id=entry_data['voice_id'],
                            voice_settings=voice_settings,
                            audio_data=audio_data,
                            created_at=entry_data['created_at'],
                            access_count=entry_data.get('access_count', 0),
                            last_accessed=entry_data.get('last_accessed', time.time())
                        )
                        
                        self.voice_cache[cache_key] = cache_entry
        
        except Exception as e:
            print(f"Warning: Failed to load voice cache: {e}")
    
    async def _save_cache(self):
        """Save voice cache to disk."""
        try:
            cache_data = {}
            
            for cache_key, entry in self.voice_cache.items():
                # Save audio data
                audio_path = f"{self.cache_dir}/audio/{cache_key}.wav"
                async with aiofiles.open(audio_path, 'wb') as f:
                    await f.write(entry.audio_data.audio_bytes)
                
                # Save metadata
                cache_data[cache_key] = {
                    'text': entry.text,
                    'language_code': entry.language_code,
                    'voice_id': entry.voice_id,
                    'voice_settings': asdict(entry.voice_settings),
                    'sample_rate': entry.audio_data.sample_rate,
                    'channels': entry.audio_data.channels,
                    'duration': entry.audio_data.duration,
                    'format': entry.audio_data.format,
                    'bit_depth': entry.audio_data.bit_depth,
                    'created_at': entry.created_at,
                    'access_count': entry.access_count,
                    'last_accessed': entry.last_accessed
                }
            
            # Save cache index
            cache_index_path = f"{self.cache_dir}/cache_index.json"
            async with aiofiles.open(cache_index_path, 'w') as f:
                await f.write(json.dumps(cache_data, indent=2))
        
        except Exception as e:
            print(f"Warning: Failed to save voice cache: {e}")
    
    def _generate_cache_key(self, text: str, language_code: str, 
                          voice_id: str, voice_settings: VoiceSettings) -> str:
        """Generate cache key for voice synthesis request."""
        cache_input = f"{text}|{language_code}|{voice_id}|{asdict(voice_settings)}"
        return hashlib.md5(cache_input.encode()).hexdigest()
    
    async def _cleanup_cache(self):
        """Clean up expired and least-used cache entries."""
        current_time = time.time()
        
        # Remove expired entries
        expired_keys = []
        for cache_key, entry in self.voice_cache.items():
            if current_time - entry.created_at > self.cache_ttl:
                expired_keys.append(cache_key)
        
        for key in expired_keys:
            del self.voice_cache[key]
            # Remove audio file
            audio_path = f"{self.cache_dir}/audio/{key}.wav"
            if os.path.exists(audio_path):
                os.remove(audio_path)
        
        # If cache is still too large, remove least-used entries
        if len(self.voice_cache) > self.max_cache_size:
            # Sort by access count and last accessed time
            sorted_entries = sorted(
                self.voice_cache.items(),
                key=lambda x: (x[1].access_count, x[1].last_accessed)
            )
            
            # Remove oldest entries
            entries_to_remove = len(self.voice_cache) - self.max_cache_size
            for i in range(entries_to_remove):
                cache_key = sorted_entries[i][0]
                del self.voice_cache[cache_key]
                # Remove audio file
                audio_path = f"{self.cache_dir}/audio/{cache_key}.wav"
                if os.path.exists(audio_path):
                    os.remove(audio_path)
    
    async def text_to_speech(self, text: str, language_code: str, 
                           voice_settings: Optional[VoiceSettings] = None) -> AudioData:
        """
        Convert text to speech using ElevenLabs API.
        
        Args:
            text: Text to convert to speech
            language_code: Language code (e.g., 'hi-IN', 'en-IN')
            voice_settings: Optional voice configuration
            
        Returns:
            AudioData containing synthesized speech
            
        Raises:
            VoiceProcessingError: If synthesis fails
        """
        if not self.api_key:
            raise VoiceProcessingError(
                "ElevenLabs API key not configured",
                error_code="MISSING_API_KEY"
            )
        
        # Get voice ID for language
        voice_id = self.language_voice_mapping.get(language_code)
        if not voice_id:
            # Fallback to English voice
            voice_id = self.language_voice_mapping["en-IN"]
            language_code = "en-IN"
        
        # Use default voice settings if not provided
        if voice_settings is None:
            voice_settings = self.default_voice_settings.get(
                language_code, 
                VoiceSettings()
            )
        
        # Check cache first
        cache_key = self._generate_cache_key(text, language_code, voice_id, voice_settings)
        if cache_key in self.voice_cache:
            cache_entry = self.voice_cache[cache_key]
            cache_entry.access_count += 1
            cache_entry.last_accessed = time.time()
            return cache_entry.audio_data
        
        try:
            # Prepare API request
            url = f"{self.base_url}/text-to-speech/{voice_id}"
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key
            }
            
            payload = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": asdict(voice_settings)
            }
            
            # Make API request
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise VoiceProcessingError(
                            f"ElevenLabs API error: {error_text}",
                            error_code="API_ERROR"
                        )
                    
                    audio_bytes = await response.read()
            
            # Convert MP3 to AudioData (simplified - in production would use proper audio conversion)
            audio_data = AudioData(
                audio_bytes=audio_bytes,
                sample_rate=22050,  # ElevenLabs default
                channels=1,
                duration=max(1.0, len(text) * 0.1),  # Estimate duration
                format="mp3",
                bit_depth=16
            )
            
            # Cache the result
            cache_entry = CachedVoiceEntry(
                text=text,
                language_code=language_code,
                voice_id=voice_id,
                voice_settings=voice_settings,
                audio_data=audio_data,
                created_at=time.time(),
                access_count=1,
                last_accessed=time.time()
            )
            
            self.voice_cache[cache_key] = cache_entry
            
            # Clean up cache if needed
            if len(self.voice_cache) > self.max_cache_size:
                await self._cleanup_cache()
            
            # Save cache periodically
            if len(self.voice_cache) % 10 == 0:
                await self._save_cache()
            
            return audio_data
            
        except aiohttp.ClientError as e:
            raise VoiceProcessingError(
                f"Network error during TTS synthesis: {str(e)}",
                error_code="NETWORK_ERROR",
                original_error=e
            )
        except Exception as e:
            raise VoiceProcessingError(
                f"TTS synthesis failed: {str(e)}",
                error_code="TTS_FAILED",
                original_error=e
            )
    
    async def get_available_voices(self) -> List[Dict[str, Any]]:
        """
        Get list of available voices from ElevenLabs.
        
        Returns:
            List of voice information dictionaries
        """
        if not self.api_key:
            raise VoiceProcessingError(
                "ElevenLabs API key not configured",
                error_code="MISSING_API_KEY"
            )
        
        try:
            url = f"{self.base_url}/voices"
            headers = {"xi-api-key": self.api_key}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise VoiceProcessingError(
                            f"Failed to get voices: {error_text}",
                            error_code="API_ERROR"
                        )
                    
                    data = await response.json()
                    return data.get("voices", [])
        
        except Exception as e:
            raise VoiceProcessingError(
                f"Failed to get available voices: {str(e)}",
                error_code="VOICES_FETCH_FAILED",
                original_error=e
            )
    
    async def clone_voice(self, name: str, audio_files: List[bytes], 
                         description: Optional[str] = None) -> str:
        """
        Clone a voice using provided audio samples.
        
        Args:
            name: Name for the cloned voice
            audio_files: List of audio file bytes for voice cloning
            description: Optional description for the voice
            
        Returns:
            Voice ID of the cloned voice
        """
        if not self.api_key:
            raise VoiceProcessingError(
                "ElevenLabs API key not configured",
                error_code="MISSING_API_KEY"
            )
        
        try:
            url = f"{self.base_url}/voices/add"
            headers = {"xi-api-key": self.api_key}
            
            # Prepare multipart form data
            data = aiohttp.FormData()
            data.add_field('name', name)
            if description:
                data.add_field('description', description)
            
            # Add audio files
            for i, audio_bytes in enumerate(audio_files):
                data.add_field(
                    'files',
                    audio_bytes,
                    filename=f'sample_{i}.wav',
                    content_type='audio/wav'
                )
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise VoiceProcessingError(
                            f"Voice cloning failed: {error_text}",
                            error_code="VOICE_CLONE_FAILED"
                        )
                    
                    result = await response.json()
                    return result.get("voice_id")
        
        except Exception as e:
            raise VoiceProcessingError(
                f"Voice cloning failed: {str(e)}",
                error_code="VOICE_CLONE_FAILED",
                original_error=e
            )
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported language codes."""
        return list(self.language_voice_mapping.keys())
    
    def is_language_supported(self, language_code: str) -> bool:
        """Check if language is supported."""
        return language_code in self.language_voice_mapping
    
    async def health_check(self) -> bool:
        """Check if ElevenLabs service is healthy."""
        try:
            if not self.api_key:
                return False
            
            # Simple API call to check connectivity
            url = f"{self.base_url}/user"
            headers = {"xi-api-key": self.api_key}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=5) as response:
                    return response.status == 200
        
        except Exception:
            return False
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get voice cache statistics."""
        total_entries = len(self.voice_cache)
        total_size = sum(len(entry.audio_data.audio_bytes) for entry in self.voice_cache.values())
        
        # Calculate hit rate (simplified)
        total_accesses = sum(entry.access_count for entry in self.voice_cache.values())
        
        return {
            "total_entries": total_entries,
            "total_size_bytes": total_size,
            "total_accesses": total_accesses,
            "cache_hit_rate": min(1.0, total_accesses / max(1, total_entries * 2)),
            "oldest_entry": min(
                (entry.created_at for entry in self.voice_cache.values()),
                default=time.time()
            ),
            "most_accessed": max(
                (entry.access_count for entry in self.voice_cache.values()),
                default=0
            )
        }
    
    async def clear_cache(self):
        """Clear all cached voice entries."""
        self.voice_cache.clear()
        
        # Remove cache files
        import shutil
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
        
        self._initialize_cache()
    
    async def preload_common_phrases(self, phrases: List[Dict[str, str]]):
        """
        Preload common phrases for faster response times.
        
        Args:
            phrases: List of dictionaries with 'text' and 'language_code' keys
        """
        for phrase_info in phrases:
            text = phrase_info.get('text')
            language_code = phrase_info.get('language_code', 'hi-IN')
            
            if text:
                try:
                    await self.text_to_speech(text, language_code)
                except Exception as e:
                    print(f"Warning: Failed to preload phrase '{text}': {e}")