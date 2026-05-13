#!/usr/bin/env python3
"""
Test script for recommendation data generation
"""

import sys
import os
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add current directory to path
sys.path.append('.')

try:
    # Import required modules
    import pandas as pd
    import numpy as np
    from sklearn.model_selection import train_test_split
    from datetime import datetime, timedelta
    import hashlib
    import uuid
    from dataclasses import dataclass, asdict
    from enum import Enum
    import json
    
    logger.info("All required modules imported successfully")
    
    # Now try to import our classes
    exec(open('utils/recommendation_dataset_preparation.py').read())
    
    logger.info("Recommendation dataset preparation module loaded")
    
    # Test creating the preparator
    output_dir = './data/recommendation_datasets'
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    preparator = UserInteractionDataPreparator(output_dir)
    logger.info("UserInteractionDataPreparator created successfully")
    
    # Generate a small dataset for testing
    logger.info("Starting dataset generation...")
    preparator.generate_complete_dataset(
        num_users=100,
        num_courses=50,
        num_interactions=1000
    )
    logger.info("Dataset generation completed!")
    
except Exception as e:
    logger.error(f"Error occurred: {e}")
    import traceback
    traceback.print_exc()