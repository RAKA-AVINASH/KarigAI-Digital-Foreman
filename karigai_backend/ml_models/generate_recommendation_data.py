#!/usr/bin/env python3
"""
Simple script to generate recommendation datasets for KarigAI
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.append('.')

# Import the data preparation utilities
from utils.recommendation_dataset_preparation import UserInteractionDataPreparator

def main():
    """Generate recommendation datasets"""
    output_dir = './data/recommendation_datasets'
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Create data preparator
    preparator = UserInteractionDataPreparator(output_dir)
    
    # Generate complete dataset
    print("Generating recommendation datasets...")
    preparator.generate_complete_dataset(
        num_users=1000,
        num_courses=500,
        num_interactions=50000
    )
    print("Dataset generation completed!")

if __name__ == "__main__":
    main()