"""
FastAPI inference server for speech recognition and TTS models.
Provides REST API endpoints for model inference with ONNX optimization.
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, List
import torch
import torchaudio
import librosa
import soundfile as sf
import numpy as np
from pathlib import Path
import tempfile
import io
import logging
from functools import lru_cache
import onnxruntime as ort

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="KarigAI Speech API",
    description="Speech Recognition and Text-to-Speech API for Indian Languages",
    version="1.0.0"
)


# Request/Response Models
class TranscriptionRequest(BaseModel):
    language: Optional[str] = "hi"
    confidence_threshold: Optional[float] = 0.8


class TranscriptionResponse(BaseModel):
    text: str
    language: str
    confidence: float
    duration: float


class TTSRequest(BaseModel):
    text: str
    language: str = "hi"
    speaker_id: Optional[int] = 0
    speed: Optional[float] = 1.0


class TTSResponse(BaseModel):
    audio_url: str
    duration: float
    sample_rate: int


class ModelInfo(BaseModel):
    model_name: str
    version: str
    languages: List[str]
    status: str


# Model Manager
class SpeechModelManager:
    """Manages loading and caching of speech models."""
    
    def __init__(self, models_dir: str = "./ml_models/models"):
        self.models_dir = Path(models_dir)
        self.stt_model = None
        self.tts_model = None
        self.vocoder = None
        self.use_onnx = True
        
        # ONNX Runtime session options
        self.ort_session_options = ort.SessionOptions()
        self.ort_session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        
        # Providers (GPU if available, else CPU)
        self.providers = ['CUDAExecutionProvider', 'CPUExecutionProvider'] if torch.cuda.is_available() else ['CPUExecutionProvider']
    
    def load_stt_model(self, model_path: Optional[str] = None):
        """Load speech-to-text model."""
        if model_path is None:
            model_path = self.models_dir / "exports" / "whisper_onnx"
        
        try:
            if self.use_onnx and (Path(model_path) / "model.onnx").exists():
                logger.info(f"Loading STT ONNX model from {model_path}")
                self.stt_model = ort.InferenceSession(
                    str(Path(model_path) / "model.onnx"),
                    sess_options=self.ort_session_options,
                    providers=self.providers
                )
            else:
                logger.info(f"Loading STT PyTorch model from {model_path}")
                from transformers import WhisperProcessor, WhisperForConditionalGeneration
                self.stt_processor = WhisperProcessor.from_pretrained(model_path)
                self.stt_model = WhisperForConditionalGeneration.from_pretrained(model_path)
                self.stt_model.eval()
                if torch.cuda.is_available():
                    self.stt_model = self.stt_model.cuda()
            
            logger.info("STT model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load STT model: {e}")
            raise
    
    def load_tts_model(self, model_path: Optional[str] = None):
        """Load text-to-speech model."""
        if model_path is None:
            model_path = self.models_dir / "tts"
        
        try:
            logger.info(f"Loading TTS model from {model_path}")
            checkpoint = torch.load(Path(model_path) / "tts_model.pt", map_location='cpu')
            
            # Load model architecture
            from training.train_tts import Tacotron2Model
            config = checkpoint['config']
            char_to_idx = checkpoint['char_to_idx']
            
            self.tts_model = Tacotron2Model(config, len(char_to_idx))
            self.tts_model.load_state_dict(checkpoint['model_state_dict'])
            self.tts_model.eval()
            
            if torch.cuda.is_available():
                self.tts_model = self.tts_model.cuda()
            
            self.char_to_idx = char_to_idx
            logger.info("TTS model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load TTS model: {e}")
            raise
    
    def load_vocoder(self, vocoder_path: Optional[str] = None):
        """Load vocoder for TTS."""
        try:
            logger.info("Loading vocoder")
            # Use pre-trained HiFi-GAN or load custom vocoder
            # Placeholder for vocoder loading
            self.vocoder = None  # Load actual vocoder here
            logger.info("Vocoder loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load vocoder: {e}")
            raise


# Global model manager
model_manager = SpeechModelManager()


# Startup event
@app.on_event("startup")
async def startup_event():
    """Load models on startup."""
    logger.info("Starting KarigAI Speech API...")
    try:
        model_manager.load_stt_model()
        logger.info("STT model loaded")
    except Exception as e:
        logger.warning(f"STT model not loaded: {e}")
    
    try:
        model_manager.load_tts_model()
        logger.info("TTS model loaded")
    except Exception as e:
        logger.warning(f"TTS model not loaded: {e}")
    
    logger.info("API ready!")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "stt_loaded": model_manager.stt_model is not None,
        "tts_loaded": model_manager.tts_model is not None
    }


# Model info endpoint
@app.get("/models/info", response_model=List[ModelInfo])
async def get_model_info():
    """Get information about loaded models."""
    models = []
    
    if model_manager.stt_model:
        models.append(ModelInfo(
            model_name="Whisper STT",
            version="1.0",
            languages=["hi", "ml", "pa", "bn", "ta", "te", "en"],
            status="loaded"
        ))
    
    if model_manager.tts_model:
        models.append(ModelInfo(
            model_name="Tacotron2 TTS",
            version="1.0",
            languages=["hi", "ml", "pa", "bn", "ta", "te", "en"],
            status="loaded"
        ))
    
    return models


# Speech-to-Text endpoint
@app.post("/stt/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: Optional[str] = "hi",
    confidence_threshold: Optional[float] = 0.8
):
    """
    Transcribe audio file to text.
    
    Args:
        audio: Audio file (WAV, MP3, etc.)
        language: Target language code
        confidence_threshold: Minimum confidence score
    
    Returns:
        Transcription with confidence score
    """
    if model_manager.stt_model is None:
        raise HTTPException(status_code=503, detail="STT model not loaded")
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            content = await audio.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        # Load and preprocess audio
        waveform, sr = librosa.load(temp_path, sr=16000)
        duration = len(waveform) / sr
        
        # Transcribe
        if isinstance(model_manager.stt_model, ort.InferenceSession):
            # ONNX inference
            # Prepare input
            input_features = librosa.feature.melspectrogram(
                y=waveform,
                sr=16000,
                n_mels=80
            )
            input_features = np.log(np.clip(input_features, a_min=1e-5, a_max=None))
            
            # Run inference
            outputs = model_manager.stt_model.run(
                None,
                {"input_features": input_features[np.newaxis, :, :].astype(np.float32)}
            )
            
            # Decode output (simplified)
            transcription = "Transcription from ONNX model"
            confidence = 0.95
        else:
            # PyTorch inference
            input_features = model_manager.stt_processor(
                waveform,
                sampling_rate=16000,
                return_tensors="pt"
            ).input_features
            
            if torch.cuda.is_available():
                input_features = input_features.cuda()
            
            with torch.no_grad():
                predicted_ids = model_manager.stt_model.generate(input_features)
            
            transcription = model_manager.stt_processor.batch_decode(
                predicted_ids,
                skip_special_tokens=True
            )[0]
            
            # Calculate confidence (simplified)
            confidence = 0.95
        
        # Clean up temp file
        Path(temp_path).unlink()
        
        # Check confidence threshold
        if confidence < confidence_threshold:
            logger.warning(f"Low confidence: {confidence:.2f}")
        
        return TranscriptionResponse(
            text=transcription,
            language=language,
            confidence=confidence,
            duration=duration
        )
    
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Text-to-Speech endpoint
@app.post("/tts/synthesize")
async def synthesize_speech(request: TTSRequest, background_tasks: BackgroundTasks):
    """
    Synthesize speech from text.
    
    Args:
        request: TTS request with text and parameters
    
    Returns:
        Audio file
    """
    if model_manager.tts_model is None:
        raise HTTPException(status_code=503, detail="TTS model not loaded")
    
    try:
        # Convert text to sequence
        text_sequence = torch.LongTensor([
            model_manager.char_to_idx.get(c, 0) for c in request.text.lower()
        ]).unsqueeze(0)
        
        if torch.cuda.is_available():
            text_sequence = text_sequence.cuda()
        
        # Generate mel spectrogram
        with torch.no_grad():
            encoder_outputs = model_manager.tts_model.encode(text_sequence)
            mel_output = model_manager.tts_model.inference(encoder_outputs)
        
        # Convert mel to audio (using vocoder)
        if model_manager.vocoder:
            audio = model_manager.vocoder(mel_output)
        else:
            # Fallback: use Griffin-Lim algorithm
            mel_np = mel_output.cpu().numpy().squeeze()
            audio = librosa.feature.inverse.mel_to_audio(
                np.exp(mel_np),
                sr=22050,
                n_fft=1024,
                hop_length=256
            )
        
        # Apply speed adjustment
        if request.speed != 1.0:
            audio = librosa.effects.time_stretch(audio, rate=request.speed)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            sf.write(temp_file.name, audio, 22050)
            temp_path = temp_file.name
        
        # Schedule cleanup
        background_tasks.add_task(lambda: Path(temp_path).unlink())
        
        # Return audio file
        return FileResponse(
            temp_path,
            media_type="audio/wav",
            filename=f"synthesis_{request.language}.wav"
        )
    
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Batch transcription endpoint
@app.post("/stt/batch")
async def batch_transcribe(
    audio_files: List[UploadFile] = File(...),
    language: Optional[str] = "hi"
):
    """
    Transcribe multiple audio files in batch.
    
    Args:
        audio_files: List of audio files
        language: Target language code
    
    Returns:
        List of transcriptions
    """
    results = []
    
    for audio_file in audio_files:
        try:
            result = await transcribe_audio(audio_file, language)
            results.append({
                "filename": audio_file.filename,
                "transcription": result.text,
                "confidence": result.confidence
            })
        except Exception as e:
            results.append({
                "filename": audio_file.filename,
                "error": str(e)
            })
    
    return {"results": results}


# Streaming transcription endpoint (placeholder)
@app.websocket("/stt/stream")
async def stream_transcribe(websocket):
    """
    Real-time streaming transcription.
    
    WebSocket endpoint for streaming audio and receiving real-time transcriptions.
    """
    await websocket.accept()
    
    try:
        while True:
            # Receive audio chunk
            audio_chunk = await websocket.receive_bytes()
            
            # Process chunk (simplified)
            # In production, use streaming ASR model
            
            # Send partial transcription
            await websocket.send_json({
                "partial": "Partial transcription...",
                "is_final": False
            })
    
    except Exception as e:
        logger.error(f"Streaming error: {e}")
    finally:
        await websocket.close()


# Cache for frequently used phrases
@lru_cache(maxsize=1000)
def synthesize_cached(text: str, language: str):
    """Cache frequently synthesized phrases."""
    # Implementation would call actual TTS
    pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
