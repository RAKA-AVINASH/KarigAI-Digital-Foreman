#!/usr/bin/env python3
"""
Run Comprehensive Tests on All KarigAI Models

This script runs the complete testing suite on all available KarigAI models,
including held-out test evaluation, cross-validation, edge case testing,
latency measurement, and resource usage analysis.
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Add the ml_models directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from testing.model_testing_framework import ModelTestingFramework

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('comprehensive_testing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ComprehensiveModelTester:
    """Orchestrates comprehensive testing of all KarigAI models"""
    
    def __init__(self, config_path: str = None):
        """Initialize the comprehensive tester"""
        self.config_path = config_path or "testing/testing_config.json"
        self.framework = ModelTestingFramework(self.config_path)
        self.results = {}
        
    def discover_models(self, models_dir: str) -> List[Dict]:
        """Discover all available models in the models directory"""
        models = []
        models_path = Path(models_dir)
        
        # Define model categories and their expected locations
        model_categories = {
            "vision_models": {
                "equipment_identification": "checkpoints/equipment_identification_best.pth",
                "crop_disease": "checkpoints/crop_disease_best.pth",
                "quality_assessment": "checkpoints/quality_assessment_best.pth",
                "pattern_analysis": "checkpoints/pattern_analysis_best.pth",
                "circuit_analysis": "checkpoints/circuit_analysis_best.pth",
                "ocr_model": "checkpoints/ocr_model_best.pth"
            },
            "speech_models": {
                "speech_recognition": "checkpoints/whisper_finetuned.pth",
                "text_to_speech": "checkpoints/tacotron2_best.pth"
            },
            "nlp_models": {
                "intent_recognition": "checkpoints/intent_classifier_best.pth",
                "translation": "checkpoints/translation_model_best.pth",
                "knowledge_retrieval": "checkpoints/knowledge_retrieval_best.pth"
            },
            "exported_models": {
                "equipment_identification_onnx": "exports/equipment_identification.onnx",
                "crop_disease_onnx": "exports/crop_disease.onnx",
                "speech_recognition_onnx": "exports/speech_recognition.onnx"
            }
        }
        
        # Check for each model
        for category, category_models in model_categories.items():
            for model_name, relative_path in category_models.items():
                model_path = models_path / relative_path
                
                if model_path.exists():
                    # Determine model type
                    model_type = self._determine_model_type(model_name)
                    
                    # Find corresponding test data
                    test_data_path = self._find_test_data(model_name)
                    
                    models.append({
                        "name": model_name,
                        "path": str(model_path),
                        "type": model_type,
                        "category": category,
                        "test_data": test_data_path,
                        "available": True
                    })
                    logger.info(f"Found model: {model_name} at {model_path}")
                else:
                    models.append({
                        "name": model_name,
                        "path": str(model_path),
                        "type": self._determine_model_type(model_name),
                        "category": category,
                        "test_data": None,
                        "available": False
                    })
                    logger.warning(f"Model not found: {model_name} at {model_path}")
        
        return models
    
    def _determine_model_type(self, model_name: str) -> str:
        """Determine the type of model based on its name"""
        if any(keyword in model_name for keyword in ["classification", "disease", "quality", "equipment", "intent"]):
            return "classification"
        elif any(keyword in model_name for keyword in ["detection", "pattern", "circuit"]):
            return "detection"
        elif "ocr" in model_name:
            return "ocr"
        elif "speech" in model_name or "whisper" in model_name:
            return "speech_recognition"
        elif "tts" in model_name or "tacotron" in model_name:
            return "text_to_speech"
        elif "translation" in model_name:
            return "translation"
        elif "retrieval" in model_name:
            return "retrieval"
        else:
            return "generic"
    
    def _find_test_data(self, model_name: str) -> str:
        """Find test data path for a model"""
        # This would be implemented based on actual test data organization
        test_data_mapping = {
            "equipment_identification": "data/test/equipment_test.json",
            "crop_disease": "data/test/crop_disease_test.json",
            "quality_assessment": "data/test/quality_test.json",
            "pattern_analysis": "data/test/pattern_test.json",
            "circuit_analysis": "data/test/circuit_test.json",
            "ocr_model": "data/test/ocr_test.json",
            "speech_recognition": "data/test/speech_test.json",
            "text_to_speech": "data/test/tts_test.json",
            "intent_recognition": "data/test/intent_test.json",
            "translation": "data/test/translation_test.json",
            "knowledge_retrieval": "data/test/knowledge_test.json"
        }
        
        return test_data_mapping.get(model_name, "data/test/generic_test.json")
    
    def run_comprehensive_testing(self, models_dir: str, output_dir: str, 
                                 test_specific_models: List[str] = None) -> Dict:
        """Run comprehensive testing on all or specific models"""
        logger.info("Starting comprehensive model testing...")
        
        # Discover available models
        discovered_models = self.discover_models(models_dir)
        
        # Filter models if specific ones are requested
        if test_specific_models:
            discovered_models = [m for m in discovered_models if m["name"] in test_specific_models]
        
        # Filter only available models
        available_models = [m for m in discovered_models if m["available"]]
        
        if not available_models:
            logger.error("No available models found for testing!")
            return {"error": "No models available"}
        
        logger.info(f"Found {len(available_models)} available models to test")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Test each model
        overall_results = {
            "test_session": {
                "timestamp": datetime.now().isoformat(),
                "models_tested": len(available_models),
                "output_directory": output_dir
            },
            "models": {},
            "summary": {}
        }
        
        successful_tests = 0
        failed_tests = 0
        
        for model_info in available_models:
            logger.info(f"Testing model: {model_info['name']}")
            
            try:
                # Run comprehensive testing
                model_results = self.framework.test_model_comprehensive(
                    model_info["name"],
                    model_info["path"],
                    model_info["test_data"],
                    model_info["type"]
                )
                
                overall_results["models"][model_info["name"]] = model_results
                
                # Check if test was successful
                if "error" not in model_results:
                    successful_tests += 1
                    logger.info(f"✅ Successfully tested {model_info['name']}")
                else:
                    failed_tests += 1
                    logger.error(f"❌ Failed to test {model_info['name']}: {model_results['error']}")
                
            except Exception as e:
                failed_tests += 1
                error_msg = f"Exception during testing: {str(e)}"
                logger.error(f"❌ Failed to test {model_info['name']}: {error_msg}")
                
                overall_results["models"][model_info["name"]] = {
                    "model_name": model_info["name"],
                    "error": error_msg,
                    "test_timestamp": datetime.now().isoformat()
                }
        
        # Generate overall summary
        overall_results["summary"] = self._generate_overall_summary(
            overall_results["models"], successful_tests, failed_tests
        )
        
        # Save results
        results_file = os.path.join(output_dir, "comprehensive_test_results.json")
        with open(results_file, 'w') as f:
            json.dump(overall_results, f, indent=2, default=str)
        
        # Generate comprehensive report
        self.framework.results = {name: result for name, result in overall_results["models"].items()}
        self.framework.generate_report(output_dir)
        
        # Generate summary report
        self._generate_summary_report(overall_results, output_dir)
        
        logger.info(f"Comprehensive testing completed!")
        logger.info(f"✅ Successful tests: {successful_tests}")
        logger.info(f"❌ Failed tests: {failed_tests}")
        logger.info(f"📊 Results saved to: {output_dir}")
        
        return overall_results
    
    def _generate_overall_summary(self, model_results: Dict, successful: int, failed: int) -> Dict:
        """Generate overall summary of all model tests"""
        summary = {
            "total_models": len(model_results),
            "successful_tests": successful,
            "failed_tests": failed,
            "success_rate": successful / len(model_results) if model_results else 0,
            "performance_summary": {},
            "recommendations": [],
            "critical_issues": []
        }
        
        # Analyze performance across all models
        accuracies = []
        latencies = []
        model_sizes = []
        
        for model_name, results in model_results.items():
            if "error" in results:
                summary["critical_issues"].append(f"{model_name}: {results['error']}")
                continue
            
            tests = results.get("tests", {})
            
            # Collect accuracy metrics
            holdout = tests.get("holdout_evaluation", {})
            if "accuracy" in holdout:
                accuracies.append(holdout["accuracy"])
            
            # Collect latency metrics
            latency = tests.get("latency", {})
            if "mean_latency_ms" in latency:
                latencies.append(latency["mean_latency_ms"])
            
            # Collect model size metrics
            resource = tests.get("resource_usage", {})
            if "model_size_mb" in resource:
                model_sizes.append(resource["model_size_mb"])
        
        # Calculate summary statistics
        if accuracies:
            summary["performance_summary"]["accuracy"] = {
                "mean": sum(accuracies) / len(accuracies),
                "min": min(accuracies),
                "max": max(accuracies),
                "models_above_90": sum(1 for acc in accuracies if acc > 0.9)
            }
        
        if latencies:
            summary["performance_summary"]["latency"] = {
                "mean_ms": sum(latencies) / len(latencies),
                "min_ms": min(latencies),
                "max_ms": max(latencies),
                "models_under_200ms": sum(1 for lat in latencies if lat < 200)
            }
        
        if model_sizes:
            summary["performance_summary"]["model_size"] = {
                "mean_mb": sum(model_sizes) / len(model_sizes),
                "min_mb": min(model_sizes),
                "max_mb": max(model_sizes),
                "total_mb": sum(model_sizes)
            }
        
        # Generate recommendations
        if summary["success_rate"] < 0.8:
            summary["recommendations"].append("Low success rate - review model training and data quality")
        
        if accuracies and sum(accuracies) / len(accuracies) < 0.85:
            summary["recommendations"].append("Average accuracy below target - consider model improvements")
        
        if latencies and sum(latencies) / len(latencies) > 300:
            summary["recommendations"].append("High average latency - consider model optimization")
        
        return summary
    
    def _generate_summary_report(self, results: Dict, output_dir: str):
        """Generate a summary report file"""
        summary_file = os.path.join(output_dir, "TESTING_SUMMARY.md")
        
        with open(summary_file, 'w') as f:
            f.write("# KarigAI Model Testing Summary\n\n")
            f.write(f"**Test Date:** {results['test_session']['timestamp']}\n")
            f.write(f"**Models Tested:** {results['test_session']['models_tested']}\n\n")
            
            summary = results["summary"]
            f.write("## Overall Results\n\n")
            f.write(f"- ✅ **Successful Tests:** {summary['successful_tests']}\n")
            f.write(f"- ❌ **Failed Tests:** {summary['failed_tests']}\n")
            f.write(f"- 📊 **Success Rate:** {summary['success_rate']:.1%}\n\n")
            
            # Performance summary
            if "performance_summary" in summary:
                f.write("## Performance Summary\n\n")
                
                perf = summary["performance_summary"]
                if "accuracy" in perf:
                    acc = perf["accuracy"]
                    f.write(f"### Accuracy\n")
                    f.write(f"- **Average:** {acc['mean']:.3f}\n")
                    f.write(f"- **Range:** {acc['min']:.3f} - {acc['max']:.3f}\n")
                    f.write(f"- **Models >90%:** {acc['models_above_90']}\n\n")
                
                if "latency" in perf:
                    lat = perf["latency"]
                    f.write(f"### Latency\n")
                    f.write(f"- **Average:** {lat['mean_ms']:.1f}ms\n")
                    f.write(f"- **Range:** {lat['min_ms']:.1f}ms - {lat['max_ms']:.1f}ms\n")
                    f.write(f"- **Models <200ms:** {lat['models_under_200ms']}\n\n")
                
                if "model_size" in perf:
                    size = perf["model_size"]
                    f.write(f"### Model Size\n")
                    f.write(f"- **Average:** {size['mean_mb']:.1f}MB\n")
                    f.write(f"- **Range:** {size['min_mb']:.1f}MB - {size['max_mb']:.1f}MB\n")
                    f.write(f"- **Total Size:** {size['total_mb']:.1f}MB\n\n")
            
            # Individual model results
            f.write("## Individual Model Results\n\n")
            for model_name, model_result in results["models"].items():
                if "error" in model_result:
                    f.write(f"### ❌ {model_name}\n")
                    f.write(f"**Status:** FAILED\n")
                    f.write(f"**Error:** {model_result['error']}\n\n")
                else:
                    tests = model_result.get("tests", {})
                    summary_info = model_result.get("summary", {})
                    
                    status_emoji = "✅" if summary_info.get("overall_status") in ["EXCELLENT", "GOOD"] else "⚠️"
                    f.write(f"### {status_emoji} {model_name}\n")
                    f.write(f"**Status:** {summary_info.get('overall_status', 'UNKNOWN')}\n")
                    
                    # Add key metrics
                    holdout = tests.get("holdout_evaluation", {})
                    if "accuracy" in holdout:
                        f.write(f"**Accuracy:** {holdout['accuracy']:.3f}\n")
                    
                    latency = tests.get("latency", {})
                    if "mean_latency_ms" in latency:
                        f.write(f"**Latency:** {latency['mean_latency_ms']:.1f}ms\n")
                    
                    target_val = tests.get("target_validation", {})
                    if "targets_met" in target_val:
                        targets_status = "✅ MET" if target_val["targets_met"] else "❌ NOT MET"
                        f.write(f"**Targets:** {targets_status}\n")
                    
                    f.write("\n")
            
            # Recommendations
            if summary.get("recommendations"):
                f.write("## Recommendations\n\n")
                for rec in summary["recommendations"]:
                    f.write(f"- {rec}\n")
                f.write("\n")
            
            # Critical issues
            if summary.get("critical_issues"):
                f.write("## Critical Issues\n\n")
                for issue in summary["critical_issues"]:
                    f.write(f"- ❌ {issue}\n")
                f.write("\n")
            
            f.write("---\n")
            f.write("*Report generated by KarigAI Model Testing Framework*\n")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Run comprehensive testing on KarigAI models')
    parser.add_argument('--models-dir', type=str, default='models/', 
                       help='Directory containing trained models')
    parser.add_argument('--output-dir', type=str, default='test_results/', 
                       help='Output directory for test results')
    parser.add_argument('--config', type=str, default='testing/testing_config.json',
                       help='Path to testing configuration file')
    parser.add_argument('--models', nargs='*', 
                       help='Specific models to test (default: all available)')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize comprehensive tester
    tester = ComprehensiveModelTester(args.config)
    
    # Run comprehensive testing
    results = tester.run_comprehensive_testing(
        args.models_dir,
        args.output_dir,
        args.models
    )
    
    # Print final summary
    if "error" not in results:
        summary = results["summary"]
        print("\n" + "="*60)
        print("COMPREHENSIVE TESTING COMPLETED")
        print("="*60)
        print(f"✅ Successful tests: {summary['successful_tests']}")
        print(f"❌ Failed tests: {summary['failed_tests']}")
        print(f"📊 Success rate: {summary['success_rate']:.1%}")
        print(f"📁 Results saved to: {args.output_dir}")
        print("="*60)
    else:
        print(f"❌ Testing failed: {results['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()