"""
Vision Data Augmentation for KarigAI

This module provides augmentation pipelines for different computer vision tasks.
"""

import albumentations as A
from albumentations.pytorch import ToTensorV2
import cv2
import numpy as np
from typing import Optional, Tuple


class VisionAugmentation:
    """Data augmentation pipelines for computer vision tasks"""
    
    def __init__(self, image_size: int = 224):
        """
        Initialize augmentation pipelines
        
        Args:
            image_size: Target image size for resizing
        """
        self.image_size = image_size
        
    def get_classification_train_transforms(self):
        """
        Training augmentation for classification tasks
        (equipment identification, quality assessment, crop disease)
        """
        return A.Compose([
            A.Resize(self.image_size, self.image_size),
            A.RandomRotate90(p=0.5),
            A.Flip(p=0.5),
            A.Transpose(p=0.5),
            A.OneOf([
                A.MotionBlur(p=0.2),
                A.MedianBlur(blur_limit=3, p=0.1),
                A.Blur(blur_limit=3, p=0.1),
            ], p=0.2),
            A.ShiftScaleRotate(
                shift_limit=0.0625, 
                scale_limit=0.2, 
                rotate_limit=45, 
                p=0.2
            ),
            A.OneOf([
                A.OpticalDistortion(p=0.3),
                A.GridDistortion(p=0.1),
                A.ElasticTransform(p=0.1),
            ], p=0.2),
            A.OneOf([
                A.CLAHE(clip_limit=2),
                A.Sharpen(),
                A.Emboss(),
                A.RandomBrightnessContrast(),
            ], p=0.3),
            A.HueSaturationValue(p=0.3),
            A.RGBShift(p=0.3),
            A.RandomGamma(p=0.2),
            A.Normalize(
                mean=[0.485, 0.456, 0.406], 
                std=[0.229, 0.224, 0.225]
            ),
            ToTensorV2(),
        ])
    
    def get_classification_val_transforms(self):
        """Validation/test augmentation for classification tasks"""
        return A.Compose([
            A.Resize(self.image_size, self.image_size),
            A.Normalize(
                mean=[0.485, 0.456, 0.406], 
                std=[0.229, 0.224, 0.225]
            ),
            ToTensorV2(),
        ])
    
    def get_ocr_train_transforms(self):
        """
        Training augmentation for OCR tasks (error code reading)
        More conservative to preserve text readability
        """
        return A.Compose([
            A.Resize(self.image_size, self.image_size),
            A.RandomBrightnessContrast(
                brightness_limit=0.2, 
                contrast_limit=0.2, 
                p=0.5
            ),
            A.GaussNoise(var_limit=(10.0, 50.0), p=0.3),
            A.Perspective(scale=(0.05, 0.1), p=0.3),
            A.Blur(blur_limit=3, p=0.2),
            A.Sharpen(alpha=(0.2, 0.5), lightness=(0.5, 1.0), p=0.3),
            A.RandomRotate90(p=0.2),
            A.Normalize(
                mean=[0.485, 0.456, 0.406], 
                std=[0.229, 0.224, 0.225]
            ),
            ToTensorV2(),
        ])
    
    def get_ocr_val_transforms(self):
        """Validation augmentation for OCR tasks"""
        return A.Compose([
            A.Resize(self.image_size, self.image_size),
            A.Normalize(
                mean=[0.485, 0.456, 0.406], 
                std=[0.229, 0.224, 0.225]
            ),
            ToTensorV2(),
        ])
    
    def get_detection_train_transforms(self):
        """
        Training augmentation for object detection tasks
        (circuit board component detection)
        """
        return A.Compose([
            A.Resize(self.image_size, self.image_size),
            A.HorizontalFlip(p=0.5),
            A.VerticalFlip(p=0.2),
            A.RandomRotate90(p=0.5),
            A.OneOf([
                A.MotionBlur(p=0.2),
                A.MedianBlur(blur_limit=3, p=0.1),
                A.Blur(blur_limit=3, p=0.1),
            ], p=0.2),
            A.ShiftScaleRotate(
                shift_limit=0.0625, 
                scale_limit=0.1, 
                rotate_limit=15, 
                p=0.3
            ),
            A.OneOf([
                A.CLAHE(clip_limit=2),
                A.Sharpen(),
                A.RandomBrightnessContrast(),
            ], p=0.3),
            A.HueSaturationValue(p=0.2),
            A.Normalize(
                mean=[0.485, 0.456, 0.406], 
                std=[0.229, 0.224, 0.225]
            ),
            ToTensorV2(),
        ], bbox_params=A.BboxParams(
            format='pascal_voc',
            label_fields=['class_labels']
        ))
    
    def get_detection_val_transforms(self):
        """Validation augmentation for object detection"""
        return A.Compose([
            A.Resize(self.image_size, self.image_size),
            A.Normalize(
                mean=[0.485, 0.456, 0.406], 
                std=[0.229, 0.224, 0.225]
            ),
            ToTensorV2(),
        ], bbox_params=A.BboxParams(
            format='pascal_voc',
            label_fields=['class_labels']
        ))
    
    def get_segmentation_train_transforms(self):
        """
        Training augmentation for segmentation tasks
        (pattern analysis, motif detection)
        """
        return A.Compose([
            A.Resize(self.image_size, self.image_size),
            A.HorizontalFlip(p=0.5),
            A.VerticalFlip(p=0.2),
            A.RandomRotate90(p=0.5),
            A.ShiftScaleRotate(
                shift_limit=0.0625, 
                scale_limit=0.1, 
                rotate_limit=45, 
                p=0.3
            ),
            A.OneOf([
                A.ElasticTransform(p=0.3),
                A.GridDistortion(p=0.2),
                A.OpticalDistortion(p=0.2),
            ], p=0.2),
            A.OneOf([
                A.CLAHE(clip_limit=2),
                A.Sharpen(),
                A.RandomBrightnessContrast(),
            ], p=0.3),
            A.HueSaturationValue(p=0.3),
            A.Normalize(
                mean=[0.485, 0.456, 0.406], 
                std=[0.229, 0.224, 0.225]
            ),
            ToTensorV2(),
        ])
    
    def get_segmentation_val_transforms(self):
        """Validation augmentation for segmentation"""
        return A.Compose([
            A.Resize(self.image_size, self.image_size),
            A.Normalize(
                mean=[0.485, 0.456, 0.406], 
                std=[0.229, 0.224, 0.225]
            ),
            ToTensorV2(),
        ])
    
    def get_quality_assessment_train_transforms(self):
        """
        Training augmentation for quality assessment
        More conservative to preserve quality indicators
        """
        return A.Compose([
            A.Resize(self.image_size, self.image_size),
            A.HorizontalFlip(p=0.5),
            A.RandomRotate90(p=0.3),
            A.ShiftScaleRotate(
                shift_limit=0.05, 
                scale_limit=0.1, 
                rotate_limit=15, 
                p=0.2
            ),
            A.RandomBrightnessContrast(
                brightness_limit=0.1, 
                contrast_limit=0.1, 
                p=0.3
            ),
            A.HueSaturationValue(
                hue_shift_limit=10, 
                sat_shift_limit=15, 
                val_shift_limit=10, 
                p=0.2
            ),
            A.Normalize(
                mean=[0.485, 0.456, 0.406], 
                std=[0.229, 0.224, 0.225]
            ),
            ToTensorV2(),
        ])
    
    def get_quality_assessment_val_transforms(self):
        """Validation augmentation for quality assessment"""
        return A.Compose([
            A.Resize(self.image_size, self.image_size),
            A.Normalize(
                mean=[0.485, 0.456, 0.406], 
                std=[0.229, 0.224, 0.225]
            ),
            ToTensorV2(),
        ])


class SyntheticErrorCodeGenerator:
    """Generate synthetic error code displays for training"""
    
    def __init__(self, image_size: Tuple[int, int] = (224, 224)):
        """
        Initialize generator
        
        Args:
            image_size: Size of generated images (width, height)
        """
        self.image_size = image_size
        
    def generate_seven_segment(
        self, 
        text: str, 
        background_color: Optional[Tuple[int, int, int]] = None,
        text_color: Optional[Tuple[int, int, int]] = None
    ) -> np.ndarray:
        """
        Generate seven-segment display style error code
        
        Args:
            text: Error code text
            background_color: RGB background color
            text_color: RGB text color
            
        Returns:
            Generated image as numpy array
        """
        if background_color is None:
            background_color = (0, 0, 0)  # Black
        if text_color is None:
            text_color = (0, 255, 0)  # Green
        
        # Create blank image
        img = np.zeros((self.image_size[1], self.image_size[0], 3), dtype=np.uint8)
        img[:] = background_color
        
        # Add text
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 2.0
        thickness = 3
        
        # Get text size
        (text_width, text_height), baseline = cv2.getTextSize(
            text, font, font_scale, thickness
        )
        
        # Center text
        x = (self.image_size[0] - text_width) // 2
        y = (self.image_size[1] + text_height) // 2
        
        cv2.putText(img, text, (x, y), font, font_scale, text_color, thickness)
        
        return img
    
    def generate_lcd_display(
        self, 
        text: str,
        add_noise: bool = True
    ) -> np.ndarray:
        """
        Generate LCD display style error code
        
        Args:
            text: Error code text
            add_noise: Whether to add realistic noise
            
        Returns:
            Generated image as numpy array
        """
        # Create white background
        img = np.ones((self.image_size[1], self.image_size[0], 3), dtype=np.uint8) * 240
        
        # Add text in black
        font = cv2.FONT_HERSHEY_PLAIN
        font_scale = 3.0
        thickness = 2
        
        (text_width, text_height), baseline = cv2.getTextSize(
            text, font, font_scale, thickness
        )
        
        x = (self.image_size[0] - text_width) // 2
        y = (self.image_size[1] + text_height) // 2
        
        cv2.putText(img, text, (x, y), font, font_scale, (0, 0, 0), thickness)
        
        if add_noise:
            # Add slight noise
            noise = np.random.normal(0, 5, img.shape).astype(np.uint8)
            img = cv2.add(img, noise)
        
        return img
    
    def generate_batch(
        self, 
        error_codes: list, 
        num_variations: int = 5
    ) -> list:
        """
        Generate batch of synthetic error code images
        
        Args:
            error_codes: List of error code strings
            num_variations: Number of variations per code
            
        Returns:
            List of (image, label) tuples
        """
        images = []
        
        for code in error_codes:
            for _ in range(num_variations):
                # Randomly choose display type
                if np.random.random() < 0.5:
                    img = self.generate_seven_segment(code)
                else:
                    img = self.generate_lcd_display(code)
                
                # Apply random augmentations
                transform = A.Compose([
                    A.Rotate(limit=10, p=0.5),
                    A.Perspective(scale=(0.05, 0.1), p=0.3),
                    A.GaussNoise(var_limit=(10, 30), p=0.3),
                    A.RandomBrightnessContrast(p=0.5),
                    A.Blur(blur_limit=3, p=0.2),
                ])
                
                augmented = transform(image=img)
                images.append((augmented['image'], code))
        
        return images


def main():
    """Example usage"""
    # Classification augmentation
    aug = VisionAugmentation(image_size=224)
    
    print("Available augmentation pipelines:")
    print("1. Classification (train/val)")
    print("2. OCR (train/val)")
    print("3. Detection (train/val)")
    print("4. Segmentation (train/val)")
    print("5. Quality Assessment (train/val)")
    
    # Generate synthetic error codes
    generator = SyntheticErrorCodeGenerator()
    error_codes = ['E01', 'E02', 'F10', 'ERR-001', '0042']
    
    print(f"\nGenerating synthetic error codes...")
    synthetic_images = generator.generate_batch(error_codes, num_variations=3)
    print(f"Generated {len(synthetic_images)} synthetic images")
    
    # Save examples
    output_dir = 'ml_models/data/vision/error_codes/raw/synthetic'
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    for i, (img, label) in enumerate(synthetic_images[:10]):
        output_path = f"{output_dir}/synthetic_{label}_{i}.png"
        cv2.imwrite(output_path, img)
    
    print(f"Saved example images to: {output_dir}")


if __name__ == '__main__':
    main()
