"""
Audio Preprocessing Utilities

This module provides utilities for audio preprocessing including noise reduction,
normalization, and quality enhancement for voice recognition.
"""

import numpy as np
from typing import Tuple, Optional
from scipy import signal
from scipy.fft import fft, ifft
import logging

from .voice_engine import AudioData

logger = logging.getLogger(__name__)


class AudioPreprocessor:
    """
    Audio preprocessing utilities for voice recognition enhancement.
    
    Provides methods for noise reduction, normalization, filtering,
    and quality assessment of audio data.
    """
    
    def __init__(self):
        self.noise_profile = None
        self.sample_rate = None
    
    def reduce_noise(self, audio: AudioData, 
                    noise_reduction_strength: float = 0.5) -> AudioData:
        """
        Apply noise reduction to audio data using spectral subtraction.
        
        Args:
            audio: Input AudioData object
            noise_reduction_strength: Strength of noise reduction (0.0 to 1.0)
            
        Returns:
            AudioData with reduced noise
        """
        try:
            # Convert to numpy array
            audio_array = audio.to_numpy()
            
            # Apply spectral subtraction noise reduction
            if len(audio_array.shape) > 1:
                # Handle multi-channel audio
                processed_channels = []
                for channel in range(audio_array.shape[1]):
                    channel_data = audio_array[:, channel]
                    processed_channel = self._spectral_subtraction(
                        channel_data, noise_reduction_strength
                    )
                    processed_channels.append(processed_channel)
                processed_audio = np.column_stack(processed_channels)
            else:
                # Handle mono audio
                processed_audio = self._spectral_subtraction(
                    audio_array, noise_reduction_strength
                )
            
            # Create new AudioData object
            result = AudioData.from_numpy(
                processed_audio,
                sample_rate=audio.sample_rate,
                channels=audio.channels,
                format=audio.format,
                bit_depth=audio.bit_depth
            )
            
            result.preprocessed = True
            result.noise_level = max(0.0, audio.noise_level - noise_reduction_strength)
            result.file_path = audio.file_path
            
            return result
            
        except Exception as e:
            logger.error(f"Noise reduction failed: {e}")
            # Return original audio if processing fails
            return audio
    
    def normalize_audio(self, audio: AudioData, 
                       target_level: float = 0.8) -> AudioData:
        """
        Normalize audio levels to prevent clipping and ensure consistent volume.
        
        Args:
            audio: Input AudioData object
            target_level: Target normalization level (0.0 to 1.0)
            
        Returns:
            AudioData with normalized levels
        """
        try:
            audio_array = audio.to_numpy().astype(np.float32)
            
            # Normalize to prevent clipping
            max_val = np.max(np.abs(audio_array))
            if max_val > 0:
                # Scale to target level
                scale_factor = target_level / max_val
                normalized_audio = audio_array * scale_factor
            else:
                normalized_audio = audio_array
            
            # Convert back to original bit depth
            if audio.bit_depth == 16:
                normalized_audio = (normalized_audio * 32767).astype(np.int16)
            elif audio.bit_depth == 24:
                normalized_audio = (normalized_audio * 8388607).astype(np.int32)
            elif audio.bit_depth == 32:
                normalized_audio = (normalized_audio * 2147483647).astype(np.int32)
            
            result = AudioData.from_numpy(
                normalized_audio,
                sample_rate=audio.sample_rate,
                channels=audio.channels,
                format=audio.format,
                bit_depth=audio.bit_depth
            )
            
            result.preprocessed = audio.preprocessed
            result.noise_level = audio.noise_level
            result.file_path = audio.file_path
            
            return result
            
        except Exception as e:
            logger.error(f"Audio normalization failed: {e}")
            return audio
    
    def apply_bandpass_filter(self, audio: AudioData, 
                             low_freq: float = 300.0, 
                             high_freq: float = 3400.0) -> AudioData:
        """
        Apply bandpass filter to focus on speech frequencies.
        
        Args:
            audio: Input AudioData object
            low_freq: Low cutoff frequency in Hz
            high_freq: High cutoff frequency in Hz
            
        Returns:
            AudioData with bandpass filter applied
        """
        try:
            audio_array = audio.to_numpy().astype(np.float32)
            
            # Design bandpass filter
            nyquist = audio.sample_rate / 2
            low = low_freq / nyquist
            high = high_freq / nyquist
            
            # Ensure frequencies are within valid range
            low = max(0.01, min(low, 0.99))
            high = max(low + 0.01, min(high, 0.99))
            
            b, a = signal.butter(4, [low, high], btype='band')
            
            # Apply filter
            if len(audio_array.shape) > 1:
                # Multi-channel
                filtered_audio = np.zeros_like(audio_array)
                for channel in range(audio_array.shape[1]):
                    filtered_audio[:, channel] = signal.filtfilt(
                        b, a, audio_array[:, channel]
                    )
            else:
                # Mono
                filtered_audio = signal.filtfilt(b, a, audio_array)
            
            # Convert back to original bit depth
            if audio.bit_depth == 16:
                filtered_audio = (filtered_audio * 32767).astype(np.int16)
            elif audio.bit_depth == 24:
                filtered_audio = (filtered_audio * 8388607).astype(np.int32)
            elif audio.bit_depth == 32:
                filtered_audio = (filtered_audio * 2147483647).astype(np.int32)
            
            result = AudioData.from_numpy(
                filtered_audio,
                sample_rate=audio.sample_rate,
                channels=audio.channels,
                format=audio.format,
                bit_depth=audio.bit_depth
            )
            
            result.preprocessed = True
            result.noise_level = audio.noise_level
            result.file_path = audio.file_path
            
            return result
            
        except Exception as e:
            logger.error(f"Bandpass filtering failed: {e}")
            return audio
    
    def assess_audio_quality(self, audio: AudioData) -> dict:
        """
        Assess audio quality metrics for voice recognition suitability.
        
        Args:
            audio: AudioData object to assess
            
        Returns:
            Dictionary containing quality metrics
        """
        try:
            audio_array = audio.to_numpy().astype(np.float32)
            
            # Calculate RMS (Root Mean Square) for volume level
            rms = np.sqrt(np.mean(audio_array ** 2))
            
            # Calculate SNR estimate
            snr_estimate = self._estimate_snr(audio_array)
            
            # Calculate zero crossing rate (indicator of speech vs noise)
            zcr = self._calculate_zero_crossing_rate(audio_array)
            
            # Calculate spectral centroid (brightness indicator)
            spectral_centroid = self._calculate_spectral_centroid(
                audio_array, audio.sample_rate
            )
            
            # Determine overall quality score
            quality_score = self._calculate_quality_score(
                rms, snr_estimate, zcr, spectral_centroid
            )
            
            return {
                'rms_level': float(rms),
                'snr_estimate': float(snr_estimate),
                'zero_crossing_rate': float(zcr),
                'spectral_centroid': float(spectral_centroid),
                'quality_score': float(quality_score),
                'duration': audio.duration,
                'sample_rate': audio.sample_rate,
                'channels': audio.channels,
                'recommendations': self._get_quality_recommendations(
                    rms, snr_estimate, zcr, quality_score
                )
            }
            
        except Exception as e:
            logger.error(f"Audio quality assessment failed: {e}")
            return {
                'error': str(e),
                'quality_score': 0.0,
                'recommendations': ['Audio quality assessment failed']
            }
    
    def _spectral_subtraction(self, audio_signal: np.ndarray, 
                            strength: float) -> np.ndarray:
        """Apply spectral subtraction for noise reduction."""
        # Simple spectral subtraction implementation
        # In production, this would use more sophisticated algorithms
        
        # Apply window function
        windowed = audio_signal * signal.windows.hann(len(audio_signal))
        
        # FFT
        spectrum = fft(windowed)
        magnitude = np.abs(spectrum)
        phase = np.angle(spectrum)
        
        # Estimate noise floor (first 10% of signal)
        noise_samples = int(len(magnitude) * 0.1)
        noise_floor = np.mean(magnitude[:noise_samples])
        
        # Subtract noise
        cleaned_magnitude = magnitude - (strength * noise_floor)
        cleaned_magnitude = np.maximum(cleaned_magnitude, 0.1 * magnitude)
        
        # Reconstruct signal
        cleaned_spectrum = cleaned_magnitude * np.exp(1j * phase)
        cleaned_signal = np.real(ifft(cleaned_spectrum))
        
        return cleaned_signal
    
    def _estimate_snr(self, audio_signal: np.ndarray) -> float:
        """Estimate Signal-to-Noise Ratio."""
        # Simple SNR estimation
        # Assume first and last 10% are noise, middle 80% is signal+noise
        signal_length = len(audio_signal)
        noise_start = int(signal_length * 0.05)
        noise_end = int(signal_length * 0.05)
        
        noise_samples = np.concatenate([
            audio_signal[:noise_start],
            audio_signal[-noise_end:]
        ])
        
        signal_samples = audio_signal[noise_start:-noise_end]
        
        noise_power = np.mean(noise_samples ** 2)
        signal_power = np.mean(signal_samples ** 2)
        
        if noise_power > 0:
            snr_linear = signal_power / noise_power
            snr_db = 10 * np.log10(snr_linear)
            return max(0.0, snr_db)
        else:
            return 40.0  # Very high SNR if no noise detected
    
    def _calculate_zero_crossing_rate(self, audio_signal: np.ndarray) -> float:
        """Calculate zero crossing rate."""
        zero_crossings = np.sum(np.abs(np.diff(np.sign(audio_signal))))
        zcr = zero_crossings / (2.0 * len(audio_signal))
        return zcr
    
    def _calculate_spectral_centroid(self, audio_signal: np.ndarray, 
                                   sample_rate: int) -> float:
        """Calculate spectral centroid (brightness measure)."""
        spectrum = np.abs(fft(audio_signal))
        freqs = np.fft.fftfreq(len(spectrum), 1/sample_rate)
        
        # Only use positive frequencies
        positive_freqs = freqs[:len(freqs)//2]
        positive_spectrum = spectrum[:len(spectrum)//2]
        
        if np.sum(positive_spectrum) > 0:
            centroid = np.sum(positive_freqs * positive_spectrum) / np.sum(positive_spectrum)
            return abs(centroid)
        else:
            return 0.0
    
    def _calculate_quality_score(self, rms: float, snr: float, 
                               zcr: float, centroid: float) -> float:
        """Calculate overall quality score (0.0 to 1.0)."""
        # Normalize metrics and combine
        rms_score = min(1.0, rms * 10)  # Assume good RMS around 0.1
        snr_score = min(1.0, snr / 20.0)  # Good SNR above 20dB
        zcr_score = 1.0 - min(1.0, zcr * 10)  # Lower ZCR is better for speech
        centroid_score = min(1.0, centroid / 2000.0)  # Speech centroid around 1-2kHz
        
        # Weighted combination
        quality_score = (
            0.3 * rms_score +
            0.4 * snr_score +
            0.2 * zcr_score +
            0.1 * centroid_score
        )
        
        return max(0.0, min(1.0, quality_score))
    
    def _get_quality_recommendations(self, rms: float, snr: float, 
                                   zcr: float, quality_score: float) -> list:
        """Get recommendations for improving audio quality."""
        recommendations = []
        
        if rms < 0.01:
            recommendations.append("Audio level is too low - speak closer to microphone")
        elif rms > 0.5:
            recommendations.append("Audio level is too high - reduce input gain")
        
        if snr < 10:
            recommendations.append("High noise level detected - find quieter environment")
        
        if zcr > 0.1:
            recommendations.append("High noise or distortion detected")
        
        if quality_score < 0.3:
            recommendations.append("Overall audio quality is poor - consider re-recording")
        elif quality_score < 0.6:
            recommendations.append("Audio quality could be improved")
        
        if not recommendations:
            recommendations.append("Audio quality is good for voice recognition")
        
        return recommendations