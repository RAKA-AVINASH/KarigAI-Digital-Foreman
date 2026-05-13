"""
Audio preprocessing utilities for speech recognition model training.
Handles audio loading, resampling, normalization, and feature extraction.
"""

import numpy as np
import librosa
import soundfile as sf
from pathlib import Path
from typing import Tuple, Optional, Dict, List
import torch
import torchaudio
from dataclasses import dataclass


@dataclass
class AudioConfig:
    """Configuration for audio preprocessing."""
    sample_rate: int = 16000
    n_fft: int = 400
    hop_length: int = 160
    n_mels: int = 80
    max_duration_seconds: float = 30.0
    min_duration_seconds: float = 1.0
    normalize: bool = True
    trim_silence: bool = True
    top_db: int = 30


class AudioPreprocessor:
    """Handles audio preprocessing for speech recognition."""
    
    def __init__(self, config: AudioConfig = None):
        self.config = config or AudioConfig()
    
    def load_audio(self, audio_path: str) -> Tuple[np.ndarray, int]:
        """
        Load audio file and return waveform and sample rate.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Tuple of (waveform, sample_rate)
        """
        try:
            # Try librosa first
            waveform, sr = librosa.load(audio_path, sr=None)
            return waveform, sr
        except Exception as e:
            # Fallback to soundfile
            try:
                waveform, sr = sf.read(audio_path)
                return waveform, sr
            except Exception as e2:
                raise ValueError(f"Failed to load audio from {audio_path}: {e}, {e2}")
    
    def resample(self, waveform: np.ndarray, orig_sr: int, target_sr: int = None) -> np.ndarray:
        """
        Resample audio to target sample rate.
        
        Args:
            waveform: Input waveform
            orig_sr: Original sample rate
            target_sr: Target sample rate (default: config.sample_rate)
            
        Returns:
            Resampled waveform
        """
        if target_sr is None:
            target_sr = self.config.sample_rate
        
        if orig_sr == target_sr:
            return waveform
        
        return librosa.resample(waveform, orig_sr=orig_sr, target_sr=target_sr)
    
    def normalize(self, waveform: np.ndarray) -> np.ndarray:
        """
        Normalize audio waveform to [-1, 1] range.
        
        Args:
            waveform: Input waveform
            
        Returns:
            Normalized waveform
        """
        max_val = np.abs(waveform).max()
        if max_val > 0:
            return waveform / max_val
        return waveform
    
    def trim_silence(self, waveform: np.ndarray, top_db: int = None) -> np.ndarray:
        """
        Trim silence from beginning and end of audio.
        
        Args:
            waveform: Input waveform
            top_db: Threshold in decibels below reference to consider as silence
            
        Returns:
            Trimmed waveform
        """
        if top_db is None:
            top_db = self.config.top_db
        
        trimmed, _ = librosa.effects.trim(waveform, top_db=top_db)
        return trimmed
    
    def pad_or_truncate(self, waveform: np.ndarray, max_length: int) -> np.ndarray:
        """
        Pad or truncate waveform to fixed length.
        
        Args:
            waveform: Input waveform
            max_length: Target length in samples
            
        Returns:
            Padded or truncated waveform
        """
        if len(waveform) > max_length:
            return waveform[:max_length]
        elif len(waveform) < max_length:
            pad_length = max_length - len(waveform)
            return np.pad(waveform, (0, pad_length), mode='constant')
        return waveform
    
    def extract_mel_spectrogram(self, waveform: np.ndarray) -> np.ndarray:
        """
        Extract mel spectrogram features from waveform.
        
        Args:
            waveform: Input waveform
            
        Returns:
            Mel spectrogram (n_mels, time_steps)
        """
        mel_spec = librosa.feature.melspectrogram(
            y=waveform,
            sr=self.config.sample_rate,
            n_fft=self.config.n_fft,
            hop_length=self.config.hop_length,
            n_mels=self.config.n_mels
        )
        
        # Convert to log scale
        log_mel_spec = librosa.power_to_db(mel_spec, ref=np.max)
        
        return log_mel_spec
    
    def extract_mfcc(self, waveform: np.ndarray, n_mfcc: int = 13) -> np.ndarray:
        """
        Extract MFCC features from waveform.
        
        Args:
            waveform: Input waveform
            n_mfcc: Number of MFCC coefficients
            
        Returns:
            MFCC features (n_mfcc, time_steps)
        """
        mfcc = librosa.feature.mfcc(
            y=waveform,
            sr=self.config.sample_rate,
            n_mfcc=n_mfcc,
            n_fft=self.config.n_fft,
            hop_length=self.config.hop_length
        )
        
        return mfcc
    
    def preprocess(self, audio_path: str, extract_features: bool = False) -> Dict:
        """
        Complete preprocessing pipeline for an audio file.
        
        Args:
            audio_path: Path to audio file
            extract_features: Whether to extract mel spectrogram features
            
        Returns:
            Dictionary with preprocessed audio and metadata
        """
        # Load audio
        waveform, orig_sr = self.load_audio(audio_path)
        
        # Resample
        if orig_sr != self.config.sample_rate:
            waveform = self.resample(waveform, orig_sr, self.config.sample_rate)
        
        # Trim silence
        if self.config.trim_silence:
            waveform = self.trim_silence(waveform)
        
        # Normalize
        if self.config.normalize:
            waveform = self.normalize(waveform)
        
        # Calculate duration
        duration = len(waveform) / self.config.sample_rate
        
        # Check duration constraints
        if duration < self.config.min_duration_seconds:
            raise ValueError(f"Audio too short: {duration:.2f}s < {self.config.min_duration_seconds}s")
        
        if duration > self.config.max_duration_seconds:
            max_samples = int(self.config.max_duration_seconds * self.config.sample_rate)
            waveform = waveform[:max_samples]
            duration = self.config.max_duration_seconds
        
        result = {
            'waveform': waveform,
            'sample_rate': self.config.sample_rate,
            'duration': duration,
            'num_samples': len(waveform)
        }
        
        # Extract features if requested
        if extract_features:
            result['mel_spectrogram'] = self.extract_mel_spectrogram(waveform)
            result['mfcc'] = self.extract_mfcc(waveform)
        
        return result


class AudioAugmentor:
    """Applies data augmentation to audio for training."""
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
    
    def add_noise(self, waveform: np.ndarray, noise_factor: float = 0.005) -> np.ndarray:
        """
        Add random noise to waveform.
        
        Args:
            waveform: Input waveform
            noise_factor: Noise intensity factor
            
        Returns:
            Noisy waveform
        """
        noise = np.random.randn(len(waveform))
        augmented = waveform + noise_factor * noise
        return augmented
    
    def time_stretch(self, waveform: np.ndarray, rate: float) -> np.ndarray:
        """
        Stretch or compress audio in time.
        
        Args:
            waveform: Input waveform
            rate: Stretch factor (>1 speeds up, <1 slows down)
            
        Returns:
            Time-stretched waveform
        """
        return librosa.effects.time_stretch(waveform, rate=rate)
    
    def pitch_shift(self, waveform: np.ndarray, n_steps: float) -> np.ndarray:
        """
        Shift pitch of audio.
        
        Args:
            waveform: Input waveform
            n_steps: Number of semitones to shift
            
        Returns:
            Pitch-shifted waveform
        """
        return librosa.effects.pitch_shift(
            waveform, 
            sr=self.sample_rate, 
            n_steps=n_steps
        )
    
    def speed_perturbation(self, waveform: np.ndarray, speed_factor: float) -> np.ndarray:
        """
        Change speed of audio (affects both pitch and tempo).
        
        Args:
            waveform: Input waveform
            speed_factor: Speed multiplier
            
        Returns:
            Speed-perturbed waveform
        """
        indices = np.round(np.arange(0, len(waveform), speed_factor)).astype(int)
        indices = indices[indices < len(waveform)]
        return waveform[indices]
    
    def augment(
        self, 
        waveform: np.ndarray, 
        augmentation_config: Dict[str, any]
    ) -> np.ndarray:
        """
        Apply random augmentations based on configuration.
        
        Args:
            waveform: Input waveform
            augmentation_config: Dictionary with augmentation parameters
            
        Returns:
            Augmented waveform
        """
        augmented = waveform.copy()
        
        # Noise injection
        if augmentation_config.get('noise_injection', False):
            if np.random.random() < 0.5:
                augmented = self.add_noise(augmented)
        
        # Speed perturbation
        if 'speed_perturbation' in augmentation_config:
            speeds = augmentation_config['speed_perturbation']
            if np.random.random() < 0.5:
                speed = np.random.choice(speeds)
                augmented = self.speed_perturbation(augmented, speed)
        
        # Pitch shift
        if 'pitch_shift' in augmentation_config:
            shifts = augmentation_config['pitch_shift']
            if np.random.random() < 0.5:
                n_steps = np.random.choice(shifts)
                augmented = self.pitch_shift(augmented, n_steps)
        
        # Time stretch
        if 'time_stretch' in augmentation_config:
            rates = augmentation_config['time_stretch']
            if np.random.random() < 0.5:
                rate = np.random.choice(rates)
                augmented = self.time_stretch(augmented, rate)
        
        return augmented


def save_audio(waveform: np.ndarray, output_path: str, sample_rate: int = 16000):
    """
    Save waveform to audio file.
    
    Args:
        waveform: Audio waveform
        output_path: Output file path
        sample_rate: Sample rate
    """
    sf.write(output_path, waveform, sample_rate)


if __name__ == "__main__":
    print("Audio preprocessing utilities loaded successfully!")
    print("Use AudioPreprocessor for preprocessing and AudioAugmentor for augmentation.")
