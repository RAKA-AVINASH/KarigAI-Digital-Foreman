#!/usr/bin/env python3
"""
Test script for the recommendation inference API
"""

import requests
import json
import time
from datetime import datetime

# API base URL
BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test health check endpoint"""
    print("Testing health check...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_model_info():
    """Test model info endpoint"""
    print("Testing model info...")
    response = requests.get(f"{BASE_URL}/models/info")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_learning_recommendations():
    """Test learning recommendations endpoint"""
    print("Testing learning recommendations...")
    
    request_data = {
        "user_id": "test_user_001",
        "top_k": 5,
        "recommendation_type": "hybrid"
    }
    
    response = requests.post(f"{BASE_URL}/recommendations/learning", json=request_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_trend_analysis():
    """Test trend analysis endpoint"""
    print("Testing trend analysis...")
    
    request_data = {
        "trade": "artisan",
        "region": "north",
        "time_horizon": 30
    }
    
    response = requests.post(f"{BASE_URL}/trends/analysis", json=request_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_price_prediction():
    """Test price prediction endpoint"""
    print("Testing price prediction...")
    
    request_data = {
        "quality_score": 85.0,
        "trade": "artisan",
        "region": "central",
        "brand_reputation": 70.0,
        "market_demand": 60.0,
        "seasonal_factor": 10.0,
        "competition_level": 3.0
    }
    
    response = requests.post(f"{BASE_URL}/pricing/predict", json=request_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_metrics():
    """Test metrics endpoint"""
    print("Testing metrics...")
    response = requests.get(f"{BASE_URL}/metrics")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_ab_testing():
    """Test A/B testing endpoints"""
    print("Testing A/B testing config...")
    response = requests.get(f"{BASE_URL}/ab-test/config")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    print("Testing A/B testing results...")
    response = requests.get(f"{BASE_URL}/ab-test/results")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def run_all_tests():
    """Run all API tests"""
    print("=" * 50)
    print("KarigAI Recommendation API Tests")
    print("=" * 50)
    print()
    
    try:
        test_health_check()
        test_model_info()
        test_learning_recommendations()
        test_trend_analysis()
        test_price_prediction()
        test_metrics()
        test_ab_testing()
        
        print("✅ All tests completed successfully!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API server.")
        print("Make sure the server is running with: python inference/recommendation_inference_api.py")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")

if __name__ == "__main__":
    run_all_tests()