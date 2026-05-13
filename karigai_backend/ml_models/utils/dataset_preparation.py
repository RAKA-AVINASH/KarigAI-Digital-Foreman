"""
Dataset preparation utilities for speech recognition.
Handles dataset downloading, splitting, and organization.
"""

import os
import json
import yaml
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import pandas as pd
from sklearn.model_selection import train_test_split
from tqdm import tqdm


@dataclass
class DatasetInfo:
    """Information about a dataset."""
    name: str
    language: str
    num_samples: int
    total_duration_hours: float
    split: str  # 'train', 'val', or 'test'
    data_path: Path


class DatasetManager:
    """Manages speech datasets for training."""
    
    def __init__(self, base_path: str = "./ml_models/data"):
        self.base_path = Path(base_path)
        self.raw_path = self.base_path / "raw"
        self.processed_path = self.base_path / "processed"
        self.cache_path = self.base_path / "cache"
        
        # Create directories
        self.raw_path.mkdir(parents=True, exist_ok=True)
        self.processed_path.mkdir(parents=True, exist_ok=True)
        self.cache_path.mkdir(parents=True, exist_ok=True)
        
        self.datasets = {}
        self.load_dataset_registry()
    
    def load_dataset_registry(self):
        """Load dataset registry from file."""
        registry_path = self.base_path / "dataset_registry.json"
        if registry_path.exists():
            with open(registry_path, 'r') as f:
                self.datasets = json.load(f)
    
    def save_dataset_registry(self):
        """Save dataset registry to file."""
        registry_path = self.base_path / "dataset_registry.json"
        with open(registry_path, 'w') as f:
            json.dump(self.datasets, f, indent=2)
    
    def register_dataset(
        self,
        name: str,
        language: str,
        audio_dir: Path,
        transcript_file: Optional[Path] = None,
        metadata: Optional[Dict] = None
    ):
        """
        Register a new dataset.
        
        Args:
            name: Dataset name
            language: Language code (e.g., 'hi', 'ml', 'en')
            audio_dir: Directory containing audio files
            transcript_file: Path to transcript file (CSV or JSON)
            metadata: Additional metadata
        """
        dataset_id = f"{name}_{language}"
        
        self.datasets[dataset_id] = {
            'name': name,
            'language': language,
            'audio_dir': str(audio_dir),
            'transcript_file': str(transcript_file) if transcript_file else None,
            'metadata': metadata or {},
            'registered_at': pd.Timestamp.now().isoformat()
        }
        
        self.save_dataset_registry()
        print(f"✅ Registered dataset: {dataset_id}")
    
    def split_dataset(
        self,
        dataset_id: str,
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        test_ratio: float = 0.1,
        random_seed: int = 42
    ) -> Dict[str, List[str]]:
        """
        Split dataset into train/val/test sets.
        
        Args:
            dataset_id: Dataset identifier
            train_ratio: Training set ratio
            val_ratio: Validation set ratio
            test_ratio: Test set ratio
            random_seed: Random seed for reproducibility
            
        Returns:
            Dictionary with file lists for each split
        """
        if dataset_id not in self.datasets:
            raise ValueError(f"Dataset {dataset_id} not found in registry")
        
        dataset = self.datasets[dataset_id]
        audio_dir = Path(dataset['audio_dir'])
        
        # Get all audio files
        audio_files = list(audio_dir.glob("*.wav")) + list(audio_dir.glob("*.mp3"))
        audio_files = [str(f) for f in audio_files]
        
        if not audio_files:
            raise ValueError(f"No audio files found in {audio_dir}")
        
        # First split: train + val vs test
        train_val, test = train_test_split(
            audio_files,
            test_size=test_ratio,
            random_state=random_seed
        )
        
        # Second split: train vs val
        val_size = val_ratio / (train_ratio + val_ratio)
        train, val = train_test_split(
            train_val,
            test_size=val_size,
            random_state=random_seed
        )
        
        splits = {
            'train': train,
            'val': val,
            'test': test
        }
        
        # Save splits
        splits_dir = self.processed_path / dataset_id
        splits_dir.mkdir(parents=True, exist_ok=True)
        
        for split_name, file_list in splits.items():
            split_file = splits_dir / f"{split_name}_files.txt"
            with open(split_file, 'w') as f:
                f.write('\n'.join(file_list))
        
        # Update registry
        self.datasets[dataset_id]['splits'] = {
            'train': len(train),
            'val': len(val),
            'test': len(test)
        }
        self.save_dataset_registry()
        
        print(f"✅ Split {dataset_id}:")
        print(f"   Train: {len(train)} samples")
        print(f"   Val: {len(val)} samples")
        print(f"   Test: {len(test)} samples")
        
        return splits
    
    def create_manifest(
        self,
        dataset_id: str,
        split: str,
        transcript_mapping: Dict[str, str],
        output_file: Optional[Path] = None
    ):
        """
        Create a manifest file for a dataset split.
        
        Args:
            dataset_id: Dataset identifier
            split: Split name ('train', 'val', or 'test')
            transcript_mapping: Dictionary mapping audio file paths to transcripts
            output_file: Output manifest file path
        """
        if dataset_id not in self.datasets:
            raise ValueError(f"Dataset {dataset_id} not found")
        
        splits_dir = self.processed_path / dataset_id
        split_file = splits_dir / f"{split}_files.txt"
        
        if not split_file.exists():
            raise ValueError(f"Split file not found: {split_file}")
        
        # Read file list
        with open(split_file, 'r') as f:
            audio_files = [line.strip() for line in f if line.strip()]
        
        # Create manifest
        manifest = []
        for audio_path in tqdm(audio_files, desc=f"Creating {split} manifest"):
            if audio_path in transcript_mapping:
                manifest.append({
                    'audio_filepath': audio_path,
                    'text': transcript_mapping[audio_path],
                    'duration': None,  # Will be filled during preprocessing
                    'language': self.datasets[dataset_id]['language']
                })
        
        # Save manifest
        if output_file is None:
            output_file = splits_dir / f"{split}_manifest.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for item in manifest:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        print(f"✅ Created manifest: {output_file} ({len(manifest)} samples)")
        
        return output_file
    
    def get_dataset_statistics(self, dataset_id: str) -> Dict:
        """
        Get statistics for a dataset.
        
        Args:
            dataset_id: Dataset identifier
            
        Returns:
            Dictionary with dataset statistics
        """
        if dataset_id not in self.datasets:
            raise ValueError(f"Dataset {dataset_id} not found")
        
        dataset = self.datasets[dataset_id]
        
        stats = {
            'name': dataset['name'],
            'language': dataset['language'],
            'total_samples': 0,
            'splits': {}
        }
        
        if 'splits' in dataset:
            stats['splits'] = dataset['splits']
            stats['total_samples'] = sum(dataset['splits'].values())
        
        return stats
    
    def list_datasets(self) -> List[Dict]:
        """
        List all registered datasets.
        
        Returns:
            List of dataset information dictionaries
        """
        datasets_list = []
        for dataset_id, info in self.datasets.items():
            datasets_list.append({
                'id': dataset_id,
                'name': info['name'],
                'language': info['language'],
                'splits': info.get('splits', {})
            })
        return datasets_list


class IndianLanguageDatasetCollector:
    """Helper class for collecting Indian language speech datasets."""
    
    SUPPORTED_LANGUAGES = {
        'hi': 'Hindi',
        'ml': 'Malayalam',
        'pa': 'Punjabi',
        'bn': 'Bengali',
        'ta': 'Tamil',
        'te': 'Telugu',
        'en': 'English (Indian)'
    }
    
    DATASET_SOURCES = {
        'common_voice': {
            'url': 'https://commonvoice.mozilla.org/',
            'languages': ['hi', 'pa', 'bn', 'ta', 'te'],
            'description': 'Mozilla Common Voice - Crowdsourced voice dataset'
        },
        'openslr': {
            'url': 'https://www.openslr.org/',
            'languages': ['hi', 'ml', 'ta', 'te', 'bn'],
            'description': 'Open Speech and Language Resources'
        },
        'indic_tts': {
            'url': 'https://www.iitm.ac.in/donlab/tts/',
            'languages': ['hi', 'ta', 'te', 'ml'],
            'description': 'IIT Madras Indic TTS Database'
        }
    }
    
    @classmethod
    def print_dataset_sources(cls):
        """Print available dataset sources."""
        print("=" * 60)
        print("Indian Language Speech Dataset Sources")
        print("=" * 60)
        print()
        
        for source_name, info in cls.DATASET_SOURCES.items():
            print(f"📦 {source_name.upper()}")
            print(f"   URL: {info['url']}")
            print(f"   Languages: {', '.join(info['languages'])}")
            print(f"   Description: {info['description']}")
            print()
        
        print("=" * 60)
        print("Manual Download Instructions:")
        print("=" * 60)
        print()
        print("1. Visit the dataset source URLs above")
        print("2. Download datasets for required languages")
        print("3. Extract to: ml_models/data/raw/<dataset_name>/")
        print("4. Use DatasetManager to register and prepare datasets")
        print()
    
    @classmethod
    def create_trade_vocabulary_template(cls, output_file: str = "trade_vocabulary.csv"):
        """
        Create a template CSV for trade-specific vocabulary collection.
        
        Args:
            output_file: Output CSV file path
        """
        template_data = {
            'trade': ['plumber', 'electrician', 'carpenter', 'mechanic'],
            'term_english': ['pipe', 'wire', 'wood', 'engine'],
            'term_hindi': ['पाइप', 'तार', 'लकड़ी', 'इंजन'],
            'term_local': ['', '', '', ''],
            'pronunciation': ['paip', 'taar', 'lakdi', 'injan'],
            'context': ['water supply', 'electrical work', 'furniture', 'vehicle repair']
        }
        
        df = pd.DataFrame(template_data)
        df.to_csv(output_file, index=False)
        
        print(f"✅ Created trade vocabulary template: {output_file}")
        print("Fill in the 'term_local' column with local dialect translations")


if __name__ == "__main__":
    print("Dataset preparation utilities loaded successfully!")
    print("\nTo get started:")
    print("1. IndianLanguageDatasetCollector.print_dataset_sources()")
    print("2. Download datasets manually")
    print("3. Use DatasetManager to register and prepare datasets")
