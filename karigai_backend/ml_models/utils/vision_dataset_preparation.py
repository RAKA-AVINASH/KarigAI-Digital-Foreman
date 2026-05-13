"""
Vision Dataset Preparation Utilities for KarigAI

This module provides tools for organizing, validating, and preparing
computer vision datasets for training.
"""

import os
import json
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from sklearn.model_selection import train_test_split
import cv2
import numpy as np
from tqdm import tqdm


class VisionDatasetManager:
    """Manage vision datasets for KarigAI computer vision models"""
    
    def __init__(self, base_dir: str = 'ml_models/data/vision'):
        """
        Initialize dataset manager
        
        Args:
            base_dir: Base directory for all vision datasets
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Dataset types
        self.dataset_types = [
            'equipment', 'error_codes', 'patterns', 
            'quality', 'circuits', 'crops'
        ]
        
    def create_dataset_structure(self, dataset_type: str):
        """
        Create directory structure for a dataset type
        
        Args:
            dataset_type: Type of dataset (equipment, error_codes, etc.)
        """
        if dataset_type not in self.dataset_types:
            raise ValueError(f"Invalid dataset type. Must be one of: {self.dataset_types}")
        
        dataset_path = self.base_dir / dataset_type
        
        # Create directories
        directories = [
            dataset_path / 'raw',
            dataset_path / 'processed' / 'train',
            dataset_path / 'processed' / 'val',
            dataset_path / 'processed' / 'test',
            dataset_path / 'annotations',
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        print(f"Created directory structure for {dataset_type}")
        
    def organize_dataset(
        self, 
        dataset_type: str, 
        source_dir: str, 
        train_ratio: float = 0.8, 
        val_ratio: float = 0.1,
        copy_files: bool = True
    ):
        """
        Organize raw images into train/val/test splits
        
        Args:
            dataset_type: Type of dataset
            source_dir: Directory containing raw images
            train_ratio: Proportion for training set (default: 0.8)
            val_ratio: Proportion for validation set (default: 0.1)
            copy_files: Whether to copy files or create symlinks
        """
        dataset_path = self.base_dir / dataset_type
        processed_path = dataset_path / 'processed'
        
        # Create directories if they don't exist
        self.create_dataset_structure(dataset_type)
        
        # Get all images
        source_path = Path(source_dir)
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
        image_files = []
        
        for ext in image_extensions:
            image_files.extend(list(source_path.rglob(f'*{ext}')))
            image_files.extend(list(source_path.rglob(f'*{ext.upper()}')))
        
        if not image_files:
            print(f"No images found in {source_dir}")
            return
        
        print(f"Found {len(image_files)} images")
        
        # Split dataset
        test_ratio = 1.0 - train_ratio - val_ratio
        
        train_files, temp_files = train_test_split(
            image_files, train_size=train_ratio, random_state=42, shuffle=True
        )
        val_files, test_files = train_test_split(
            temp_files, 
            train_size=val_ratio/(val_ratio + test_ratio), 
            random_state=42,
            shuffle=True
        )
        
        # Copy or link files to splits
        print("Organizing files...")
        self._organize_files(train_files, processed_path / 'train', copy_files)
        self._organize_files(val_files, processed_path / 'val', copy_files)
        self._organize_files(test_files, processed_path / 'test', copy_files)
        
        print(f"\nDataset organized:")
        print(f"  Train: {len(train_files)} images ({train_ratio*100:.1f}%)")
        print(f"  Val: {len(val_files)} images ({val_ratio*100:.1f}%)")
        print(f"  Test: {len(test_files)} images ({test_ratio*100:.1f}%)")
        
    def _organize_files(self, files: List[Path], dest_dir: Path, copy_files: bool = True):
        """
        Copy or link files to destination directory
        
        Args:
            files: List of file paths
            dest_dir: Destination directory
            copy_files: Whether to copy files or create symlinks
        """
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        for file in tqdm(files, desc=f"Processing {dest_dir.name}"):
            dest_file = dest_dir / file.name
            
            # Handle duplicate filenames
            counter = 1
            while dest_file.exists():
                stem = file.stem
                suffix = file.suffix
                dest_file = dest_dir / f"{stem}_{counter}{suffix}"
                counter += 1
            
            if copy_files:
                shutil.copy2(file, dest_file)
            else:
                # Create symlink (Unix-like systems)
                try:
                    os.symlink(file.absolute(), dest_file)
                except OSError:
                    # Fallback to copy on Windows or if symlink fails
                    shutil.copy2(file, dest_file)
    
    def validate_dataset(self, dataset_type: str, fix_corrupted: bool = False) -> Dict:
        """
        Validate dataset integrity
        
        Args:
            dataset_type: Type of dataset to validate
            fix_corrupted: Whether to remove corrupted images
            
        Returns:
            Dictionary with validation results
        """
        dataset_path = self.base_dir / dataset_type / 'processed'
        results = {}
        
        print(f"\nValidating {dataset_type} dataset...")
        
        for split in ['train', 'val', 'test']:
            split_path = dataset_path / split
            if not split_path.exists():
                print(f"Warning: {split} split not found")
                results[split] = {'status': 'missing'}
                continue
            
            images = list(split_path.glob('*.jpg')) + \
                    list(split_path.glob('*.jpeg')) + \
                    list(split_path.glob('*.png')) + \
                    list(split_path.glob('*.bmp'))
            
            # Check image integrity
            corrupted = []
            valid_images = []
            
            for img_path in tqdm(images, desc=f"Validating {split}"):
                try:
                    img = cv2.imread(str(img_path))
                    if img is None or img.size == 0:
                        corrupted.append(img_path)
                    else:
                        valid_images.append(img_path)
                except Exception as e:
                    corrupted.append(img_path)
            
            results[split] = {
                'status': 'ok' if not corrupted else 'has_corrupted',
                'total': len(images),
                'valid': len(valid_images),
                'corrupted': len(corrupted),
                'corrupted_files': [str(f) for f in corrupted[:10]]  # First 10
            }
            
            print(f"\n{split}:")
            print(f"  Total: {len(images)} images")
            print(f"  Valid: {len(valid_images)} images")
            print(f"  Corrupted: {len(corrupted)} images")
            
            if corrupted and fix_corrupted:
                print(f"  Removing {len(corrupted)} corrupted images...")
                for img_path in corrupted:
                    img_path.unlink()
        
        return results
    
    def generate_manifest(self, dataset_type: str) -> Dict:
        """
        Generate manifest file for dataset
        
        Args:
            dataset_type: Type of dataset
            
        Returns:
            Manifest dictionary
        """
        dataset_path = self.base_dir / dataset_type / 'processed'
        manifest = {
            'dataset_type': dataset_type,
            'base_path': str(dataset_path),
            'splits': {},
            'statistics': {}
        }
        
        total_images = 0
        
        for split in ['train', 'val', 'test']:
            split_path = dataset_path / split
            if split_path.exists():
                images = list(split_path.glob('*.jpg')) + \
                        list(split_path.glob('*.jpeg')) + \
                        list(split_path.glob('*.png')) + \
                        list(split_path.glob('*.bmp'))
                
                num_images = len(images)
                total_images += num_images
                
                manifest['splits'][split] = {
                    'num_images': num_images,
                    'path': str(split_path),
                    'image_files': [img.name for img in images[:100]]  # First 100
                }
        
        # Calculate statistics
        for split in manifest['splits']:
            num = manifest['splits'][split]['num_images']
            manifest['statistics'][split] = {
                'count': num,
                'percentage': (num / total_images * 100) if total_images > 0 else 0
            }
        
        manifest['statistics']['total'] = total_images
        
        # Save manifest
        manifest_path = dataset_path / 'manifest.json'
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        print(f"\nManifest saved to: {manifest_path}")
        print(f"Total images: {total_images}")
        
        return manifest
    
    def analyze_dataset(self, dataset_type: str, split: str = 'train') -> Dict:
        """
        Analyze dataset statistics
        
        Args:
            dataset_type: Type of dataset
            split: Dataset split to analyze
            
        Returns:
            Dictionary with analysis results
        """
        dataset_path = self.base_dir / dataset_type / 'processed' / split
        
        if not dataset_path.exists():
            print(f"Split {split} not found")
            return {}
        
        images = list(dataset_path.glob('*.jpg')) + \
                list(dataset_path.glob('*.jpeg')) + \
                list(dataset_path.glob('*.png'))
        
        if not images:
            print("No images found")
            return {}
        
        print(f"\nAnalyzing {len(images)} images from {split} split...")
        
        # Collect statistics
        widths = []
        heights = []
        aspects = []
        sizes = []
        
        for img_path in tqdm(images[:1000], desc="Analyzing"):  # Sample first 1000
            try:
                img = cv2.imread(str(img_path))
                if img is not None:
                    h, w = img.shape[:2]
                    widths.append(w)
                    heights.append(h)
                    aspects.append(w / h)
                    sizes.append(img_path.stat().st_size / 1024)  # KB
            except Exception:
                continue
        
        analysis = {
            'num_images': len(images),
            'width': {
                'min': int(np.min(widths)) if widths else 0,
                'max': int(np.max(widths)) if widths else 0,
                'mean': int(np.mean(widths)) if widths else 0,
                'median': int(np.median(widths)) if widths else 0,
            },
            'height': {
                'min': int(np.min(heights)) if heights else 0,
                'max': int(np.max(heights)) if heights else 0,
                'mean': int(np.mean(heights)) if heights else 0,
                'median': int(np.median(heights)) if heights else 0,
            },
            'aspect_ratio': {
                'min': float(np.min(aspects)) if aspects else 0,
                'max': float(np.max(aspects)) if aspects else 0,
                'mean': float(np.mean(aspects)) if aspects else 0,
            },
            'file_size_kb': {
                'min': float(np.min(sizes)) if sizes else 0,
                'max': float(np.max(sizes)) if sizes else 0,
                'mean': float(np.mean(sizes)) if sizes else 0,
            }
        }
        
        print("\nDataset Analysis:")
        print(f"  Images analyzed: {len(widths)}")
        print(f"  Width: {analysis['width']['min']}-{analysis['width']['max']} "
              f"(mean: {analysis['width']['mean']})")
        print(f"  Height: {analysis['height']['min']}-{analysis['height']['max']} "
              f"(mean: {analysis['height']['mean']})")
        print(f"  Aspect ratio: {analysis['aspect_ratio']['min']:.2f}-"
              f"{analysis['aspect_ratio']['max']:.2f} "
              f"(mean: {analysis['aspect_ratio']['mean']:.2f})")
        print(f"  File size: {analysis['file_size_kb']['min']:.1f}-"
              f"{analysis['file_size_kb']['max']:.1f} KB "
              f"(mean: {analysis['file_size_kb']['mean']:.1f} KB)")
        
        return analysis
    
    def create_sample_dataset(self, dataset_type: str, num_samples: int = 100):
        """
        Create a small sample dataset for testing
        
        Args:
            dataset_type: Type of dataset
            num_samples: Number of samples per split
        """
        dataset_path = self.base_dir / dataset_type / 'processed'
        sample_path = self.base_dir / dataset_type / 'sample'
        
        for split in ['train', 'val', 'test']:
            split_path = dataset_path / split
            sample_split_path = sample_path / split
            sample_split_path.mkdir(parents=True, exist_ok=True)
            
            if split_path.exists():
                images = list(split_path.glob('*.jpg')) + \
                        list(split_path.glob('*.png'))
                
                # Sample random images
                sample_images = np.random.choice(
                    images, 
                    min(num_samples, len(images)), 
                    replace=False
                )
                
                for img in sample_images:
                    shutil.copy2(img, sample_split_path / img.name)
                
                print(f"Created {len(sample_images)} samples for {split}")
        
        print(f"\nSample dataset created at: {sample_path}")


def main():
    """Example usage"""
    manager = VisionDatasetManager()
    
    # Create all dataset structures
    for dataset_type in manager.dataset_types:
        manager.create_dataset_structure(dataset_type)
    
    print("\nDataset structures created successfully!")
    print(f"Base directory: {manager.base_dir}")
    print("\nNext steps:")
    print("1. Place raw images in the 'raw' directories")
    print("2. Run organize_dataset() to split into train/val/test")
    print("3. Run validate_dataset() to check integrity")
    print("4. Run generate_manifest() to create manifest files")


if __name__ == '__main__':
    main()
