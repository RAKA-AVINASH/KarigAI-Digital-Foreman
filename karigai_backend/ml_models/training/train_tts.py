"""
Training script for text-to-speech synthesis model.
Based on Tacotron2/FastSpeech2 architecture for Indian languages.
"""

import os
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import torchaudio
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json
import mlflow
from tqdm import tqdm


@dataclass
class TTSConfig:
    """Configuration for TTS training."""
    model_type: str = "tacotron2"  # or "fastspeech2"
    languages: List[str] = None
    
    # Audio parameters
    sample_rate: int = 22050
    n_fft: int = 1024
    hop_length: int = 256
    win_length: int = 1024
    n_mels: int = 80
    
    # Training hyperparameters
    batch_size: int = 16
    learning_rate: float = 1e-4
    num_epochs: int = 100
    warmup_steps: int = 1000
    
    # Model-specific
    encoder_embedding_dim: int = 512
    encoder_n_convolutions: int = 3
    decoder_rnn_dim: int = 1024
    attention_dim: int = 128
    
    # Paths
    data_dir: str = "./ml_models/data/processed"
    output_dir: str = "./ml_models/models/tts"
    checkpoint_dir: str = "./ml_models/models/checkpoints/tts"
    
    def __post_init__(self):
        if self.languages is None:
            self.languages = ['hi', 'ml', 'pa', 'bn', 'ta', 'te', 'en']


class TTSDataset(Dataset):
    """Dataset for TTS training."""
    
    def __init__(
        self,
        manifest_file: str,
        sample_rate: int = 22050,
        n_mels: int = 80,
        hop_length: int = 256
    ):
        self.sample_rate = sample_rate
        self.n_mels = n_mels
        self.hop_length = hop_length
        
        # Load manifest
        self.samples = []
        with open(manifest_file, 'r', encoding='utf-8') as f:
            for line in f:
                self.samples.append(json.loads(line))
        
        # Initialize mel spectrogram transform
        self.mel_transform = torchaudio.transforms.MelSpectrogram(
            sample_rate=sample_rate,
            n_fft=1024,
            hop_length=hop_length,
            n_mels=n_mels
        )
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        sample = self.samples[idx]
        
        # Load audio
        waveform, sr = torchaudio.load(sample['audio_filepath'])
        
        # Resample if needed
        if sr != self.sample_rate:
            resampler = torchaudio.transforms.Resample(sr, self.sample_rate)
            waveform = resampler(waveform)
        
        # Convert to mono if stereo
        if waveform.shape[0] > 1:
            waveform = torch.mean(waveform, dim=0, keepdim=True)
        
        # Extract mel spectrogram
        mel_spec = self.mel_transform(waveform)
        mel_spec = torch.log(torch.clamp(mel_spec, min=1e-5))
        
        # Get text
        text = sample['text']
        
        return {
            'text': text,
            'mel_spec': mel_spec.squeeze(0),
            'waveform': waveform.squeeze(0)
        }


class Tacotron2Model(nn.Module):
    """Simplified Tacotron2 model for TTS."""
    
    def __init__(self, config: TTSConfig, vocab_size: int):
        super().__init__()
        self.config = config
        
        # Encoder
        self.embedding = nn.Embedding(vocab_size, config.encoder_embedding_dim)
        
        self.encoder_convolutions = nn.ModuleList([
            nn.Sequential(
                nn.Conv1d(
                    config.encoder_embedding_dim,
                    config.encoder_embedding_dim,
                    kernel_size=5,
                    padding=2
                ),
                nn.BatchNorm1d(config.encoder_embedding_dim),
                nn.ReLU(),
                nn.Dropout(0.5)
            )
            for _ in range(config.encoder_n_convolutions)
        ])
        
        self.encoder_lstm = nn.LSTM(
            config.encoder_embedding_dim,
            config.encoder_embedding_dim // 2,
            num_layers=1,
            batch_first=True,
            bidirectional=True
        )
        
        # Attention
        self.attention = nn.MultiheadAttention(
            config.encoder_embedding_dim,
            num_heads=4,
            batch_first=True
        )
        
        # Decoder
        self.decoder_lstm = nn.LSTM(
            config.encoder_embedding_dim + config.n_mels,
            config.decoder_rnn_dim,
            num_layers=2,
            batch_first=True
        )
        
        self.mel_projection = nn.Linear(config.decoder_rnn_dim, config.n_mels)
        self.stop_projection = nn.Linear(config.decoder_rnn_dim, 1)
    
    def encode(self, text_inputs):
        """Encode text inputs."""
        # Embedding
        x = self.embedding(text_inputs)
        x = x.transpose(1, 2)
        
        # Convolutions
        for conv in self.encoder_convolutions:
            x = conv(x)
        
        x = x.transpose(1, 2)
        
        # LSTM
        outputs, _ = self.encoder_lstm(x)
        
        return outputs
    
    def forward(self, text_inputs, mel_targets=None):
        """Forward pass."""
        # Encode text
        encoder_outputs = self.encode(text_inputs)
        
        if mel_targets is not None:
            # Teacher forcing during training
            batch_size, mel_len, _ = mel_targets.shape
            
            # Initialize decoder input
            decoder_input = torch.zeros(batch_size, 1, self.config.n_mels).to(text_inputs.device)
            
            mel_outputs = []
            stop_tokens = []
            
            for t in range(mel_len):
                # Attention
                context, _ = self.attention(
                    decoder_input,
                    encoder_outputs,
                    encoder_outputs
                )
                
                # Concatenate context and previous mel
                decoder_input_combined = torch.cat([context, decoder_input], dim=-1)
                
                # Decode
                decoder_output, _ = self.decoder_lstm(decoder_input_combined)
                
                # Project to mel
                mel_output = self.mel_projection(decoder_output)
                stop_token = self.stop_projection(decoder_output)
                
                mel_outputs.append(mel_output)
                stop_tokens.append(stop_token)
                
                # Use ground truth for next step (teacher forcing)
                decoder_input = mel_targets[:, t:t+1, :]
            
            mel_outputs = torch.cat(mel_outputs, dim=1)
            stop_tokens = torch.cat(stop_tokens, dim=1)
            
            return mel_outputs, stop_tokens
        else:
            # Inference mode
            return self.inference(encoder_outputs)
    
    def inference(self, encoder_outputs, max_length=1000):
        """Generate mel spectrogram during inference."""
        batch_size = encoder_outputs.shape[0]
        decoder_input = torch.zeros(batch_size, 1, self.config.n_mels).to(encoder_outputs.device)
        
        mel_outputs = []
        
        for _ in range(max_length):
            # Attention
            context, _ = self.attention(
                decoder_input,
                encoder_outputs,
                encoder_outputs
            )
            
            # Decode
            decoder_input_combined = torch.cat([context, decoder_input], dim=-1)
            decoder_output, _ = self.decoder_lstm(decoder_input_combined)
            
            # Project
            mel_output = self.mel_projection(decoder_output)
            stop_token = torch.sigmoid(self.stop_projection(decoder_output))
            
            mel_outputs.append(mel_output)
            
            # Check stop condition
            if stop_token.item() > 0.5:
                break
            
            decoder_input = mel_output
        
        return torch.cat(mel_outputs, dim=1)


class TTSTrainer:
    """Trainer for TTS model."""
    
    def __init__(self, config: TTSConfig):
        self.config = config
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Create character vocabulary (simplified)
        self.char_to_idx = self._create_vocabulary()
        self.vocab_size = len(self.char_to_idx)
        
        # Initialize model
        self.model = Tacotron2Model(config, self.vocab_size).to(self.device)
        
        # Optimizer
        self.optimizer = torch.optim.Adam(
            self.model.parameters(),
            lr=config.learning_rate
        )
        
        # Loss functions
        self.mel_loss = nn.MSELoss()
        self.stop_loss = nn.BCEWithLogitsLoss()
        
        # Create directories
        Path(config.output_dir).mkdir(parents=True, exist_ok=True)
        Path(config.checkpoint_dir).mkdir(parents=True, exist_ok=True)
    
    def _create_vocabulary(self):
        """Create character-to-index mapping."""
        # Basic ASCII + Devanagari characters (simplified)
        chars = list("abcdefghijklmnopqrstuvwxyz0123456789 .,!?'-")
        
        # Add Devanagari characters (Hindi)
        devanagari_start = 0x0900
        devanagari_end = 0x097F
        for code in range(devanagari_start, devanagari_end + 1):
            chars.append(chr(code))
        
        # Add special tokens
        chars = ['<pad>', '<sos>', '<eos>'] + chars
        
        return {char: idx for idx, char in enumerate(chars)}
    
    def text_to_sequence(self, text):
        """Convert text to sequence of indices."""
        sequence = [self.char_to_idx.get(char, 0) for char in text.lower()]
        return torch.LongTensor(sequence)
    
    def train_epoch(self, dataloader, epoch):
        """Train for one epoch."""
        self.model.train()
        total_loss = 0
        
        progress_bar = tqdm(dataloader, desc=f"Epoch {epoch}")
        
        for batch in progress_bar:
            # Prepare inputs
            texts = [self.text_to_sequence(text) for text in batch['text']]
            text_inputs = nn.utils.rnn.pad_sequence(texts, batch_first=True).to(self.device)
            mel_targets = batch['mel_spec'].to(self.device)
            
            # Forward pass
            mel_outputs, stop_tokens = self.model(text_inputs, mel_targets)
            
            # Calculate loss
            mel_loss = self.mel_loss(mel_outputs, mel_targets)
            
            # Create stop token targets (1 for last frame, 0 otherwise)
            stop_targets = torch.zeros_like(stop_tokens)
            stop_targets[:, -1] = 1.0
            stop_loss = self.stop_loss(stop_tokens, stop_targets)
            
            loss = mel_loss + stop_loss
            
            # Backward pass
            self.optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
            self.optimizer.step()
            
            total_loss += loss.item()
            progress_bar.set_postfix({'loss': loss.item()})
        
        return total_loss / len(dataloader)
    
    def train(self, train_dataset, val_dataset=None):
        """Train the TTS model."""
        train_loader = DataLoader(
            train_dataset,
            batch_size=self.config.batch_size,
            shuffle=True,
            num_workers=4
        )
        
        with mlflow.start_run(run_name="tts_training"):
            mlflow.log_params({
                "model_type": self.config.model_type,
                "batch_size": self.config.batch_size,
                "learning_rate": self.config.learning_rate,
                "num_epochs": self.config.num_epochs
            })
            
            for epoch in range(1, self.config.num_epochs + 1):
                train_loss = self.train_epoch(train_loader, epoch)
                
                print(f"Epoch {epoch}: Train Loss = {train_loss:.4f}")
                mlflow.log_metric("train_loss", train_loss, step=epoch)
                
                # Save checkpoint
                if epoch % 10 == 0:
                    self.save_checkpoint(epoch)
            
            # Save final model
            self.save_model()
    
    def save_checkpoint(self, epoch):
        """Save training checkpoint."""
        checkpoint_path = Path(self.config.checkpoint_dir) / f"checkpoint_epoch_{epoch}.pt"
        torch.save({
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'char_to_idx': self.char_to_idx
        }, checkpoint_path)
        print(f"Checkpoint saved: {checkpoint_path}")
    
    def save_model(self):
        """Save final model."""
        model_path = Path(self.config.output_dir) / "tts_model.pt"
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'config': self.config,
            'char_to_idx': self.char_to_idx
        }, model_path)
        print(f"Model saved: {model_path}")


def main():
    """Main training function."""
    config = TTSConfig(
        model_type="tacotron2",
        languages=['hi'],
        batch_size=16,
        num_epochs=100
    )
    
    # Load dataset
    train_dataset = TTSDataset(
        manifest_file="./ml_models/data/processed/tts_hi/train_manifest.json",
        sample_rate=config.sample_rate,
        n_mels=config.n_mels
    )
    
    # Initialize trainer
    trainer = TTSTrainer(config)
    
    # Train
    trainer.train(train_dataset)


if __name__ == "__main__":
    main()
