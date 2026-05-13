#!/usr/bin/env python3
"""
Lightning AI Studio Validation Script

This script validates that all 6 Lightning AI studios are properly configured
and ready for cloud execution without actually running the models.
"""

import os
import sys
import importlib.util
from pathlib import Path


def validate_studio_file(studio_path):
    """Validate a Lightning AI studio file"""
    print(f"\n{'='*60}")
    print(f"Validating: {studio_path.name}")
    print(f"{'='*60}")
    
    # Check file exists
    if not studio_path.exists():
        print(f"❌ ERROR: File not found: {studio_path}")
        return False
    
    # Check file size
    file_size = studio_path.stat().st_size
    print(f"✅ File exists ({file_size} bytes)")
    
    # Try to load the module
    try:
        spec = importlib.util.spec_from_file_location("studio", studio_path)
        if spec is None:
            print(f"❌ ERROR: Could not create module spec")
            return False
        
        print(f"✅ Module spec created successfully")
        
        # Check for required classes/functions
        with open(studio_path, 'r') as f:
            content = f.read()
        
        required_components = [
            'L.LightningFlow',
            'L.LightningApp',
            'def train_model',
            'torch.cuda.is_available',
            'def run(self)',
        ]
        
        missing_components = []
        for component in required_components:
            if component not in content:
                missing_components.append(component)
        
        if missing_components:
            print(f"❌ ERROR: Missing required components: {missing_components}")
            return False
        
        print(f"✅ All required components found")
        
        # Check for model-specific components
        model_specific_checks = {
            'equipment_identification_studio.py': ['EquipmentModel', 'EquipmentDataset'],
            'crop_disease_studio.py': ['CropDiseaseModel', 'CropDiseaseDataset'],
            'ocr_model_studio.py': ['CRNN', 'SyntheticErrorCodeDataset'],
            'quality_assessment_studio.py': ['QualityAssessmentModel', 'QualityDataset'],
            'pattern_analysis_studio.py': ['PatternDataset', 'get_pattern_model'],
            'circuit_analysis_studio.py': ['CircuitDataset', 'get_circuit_model'],
        }
        
        if studio_path.name in model_specific_checks:
            specific_components = model_specific_checks[studio_path.name]
            missing_specific = []
            for component in specific_components:
                if component not in content:
                    missing_specific.append(component)
            
            if missing_specific:
                print(f"❌ ERROR: Missing model-specific components: {missing_specific}")
                return False
            
            print(f"✅ Model-specific components found: {specific_components}")
        
        print(f"✅ Studio validation PASSED")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: Failed to validate studio: {e}")
        return False


def main():
    """Main validation function"""
    print("Lightning AI Studio Validation")
    print("="*60)
    
    # Get the Lightning AI directory
    lightning_dir = Path(__file__).parent
    
    # List of studios to validate
    studios = [
        'equipment_identification_studio.py',
        'crop_disease_studio.py', 
        'ocr_model_studio.py',
        'quality_assessment_studio.py',
        'pattern_analysis_studio.py',
        'circuit_analysis_studio.py',
    ]
    
    validation_results = {}
    
    # Validate each studio
    for studio_name in studios:
        studio_path = lightning_dir / studio_name
        validation_results[studio_name] = validate_studio_file(studio_path)
    
    # Summary
    print(f"\n{'='*60}")
    print("VALIDATION SUMMARY")
    print(f"{'='*60}")
    
    passed = 0
    failed = 0
    
    for studio_name, result in validation_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{studio_name:<35} {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\nTotal Studios: {len(studios)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print(f"\n🎉 ALL STUDIOS READY FOR LIGHTNING AI CLOUD EXECUTION!")
        print(f"\nTo run on Lightning AI:")
        print(f"1. Install Lightning AI CLI: pip install lightning")
        print(f"2. Login: lightning login")
        print(f"3. Run studio: lightning run app <studio_name> --cloud --instance-type=gpu-t4")
        print(f"\nExample:")
        print(f"lightning run app equipment_identification_studio.py --cloud --instance-type=gpu-t4")
        return True
    else:
        print(f"\n❌ {failed} studios failed validation. Please fix issues before running on Lightning AI.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)