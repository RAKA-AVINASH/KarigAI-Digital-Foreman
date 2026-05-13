#!/usr/bin/env python3
"""
Simple data generation for recommendation system
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import hashlib
import uuid
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_recommendation_data():
    """Generate synthetic recommendation data"""
    
    output_dir = Path('./data/recommendation_datasets')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Trade types
    trades = ['plumber', 'electrician', 'carpenter', 'mason', 'welder', 
              'appliance_repair', 'mobile_repair', 'farmer', 'artisan', 'homestay_owner']
    
    # Skill levels
    skill_levels = ['beginner', 'intermediate', 'advanced', 'expert']
    
    # Languages
    languages = ['hi', 'en', 'ml', 'pa', 'bn', 'ta', 'te', 'gu', 'mr', 'kn']
    
    # Course categories
    categories = ['basic_skills', 'safety', 'tools', 'troubleshooting', 
                  'advanced_techniques', 'business_skills', 'digital_literacy',
                  'quality_control', 'customer_service', 'maintenance',
                  'government_schemes', 'financial_planning', 'marketing']
    
    # Interaction types
    interaction_types = ['course_view', 'course_start', 'course_complete', 'course_pause',
                        'quiz_attempt', 'quiz_pass', 'quiz_fail', 'video_watch',
                        'bookmark', 'share', 'rate', 'comment', 'search', 'download_offline']
    
    # Generate users
    logger.info("Generating users...")
    users = []
    for i in range(1000):
        user_id = f'USER_{i:05d}'
        anonymized_id = hashlib.sha256(f"{user_id}salt123".encode()).hexdigest()[:16]
        
        user = {
            'user_id': user_id,
            'anonymized_id': anonymized_id,
            'trade': np.random.choice(trades),
            'skill_level': np.random.choice(skill_levels),
            'age': np.random.randint(18, 65),
            'location_type': np.random.choice(['urban', 'semi-urban', 'rural']),
            'primary_language': np.random.choice(languages),
            'secondary_languages': [np.random.choice(languages) for _ in range(np.random.randint(0, 3))],
            'registration_date': (datetime.now() - timedelta(days=np.random.randint(1, 365))).isoformat(),
            'active_days': np.random.randint(1, 100),
            'total_courses_completed': np.random.randint(0, 50),
            'avg_session_duration_minutes': np.random.randint(5, 60),
            'preferred_learning_time': np.random.choice(['morning', 'afternoon', 'evening', 'night']),
            'device_type': np.random.choice(['android', 'ios', 'web']),
            'network_quality': np.random.choice(['good', 'moderate', 'poor']),
            'privacy_consent': True,
            'data_sharing_consent': bool(np.random.choice([True, False]))
        }
        users.append(user)
    
    # Generate courses
    logger.info("Generating courses...")
    courses = []
    for i in range(500):
        course_id = f'COURSE_{i:05d}'
        trade = np.random.choice(trades)
        category = np.random.choice(categories)
        difficulty = np.random.choice(skill_levels)
        language = np.random.choice(languages)
        
        title = f"{trade.replace('_', ' ').title()} - {category.replace('_', ' ').title()} (Part {i % 10 + 1})"
        content_hash = hashlib.md5(f"{title}{category}{trade}".encode()).hexdigest()[:16]
        
        course = {
            'course_id': course_id,
            'title': title,
            'category': category,
            'trade': trade,
            'difficulty': difficulty,
            'duration_seconds': np.random.randint(30, 300),
            'language': language,
            'has_video': bool(np.random.choice([True, False])),
            'has_quiz': bool(np.random.choice([True, False])),
            'has_practical': bool(np.random.choice([True, False])),
            'prerequisites': [],
            'topics': [category, trade],
            'avg_rating': float(np.random.uniform(3.0, 5.0)),
            'num_ratings': int(np.random.randint(0, 1000)),
            'completion_rate': float(np.random.uniform(0.3, 0.95)),
            'created_date': (datetime.now() - timedelta(days=np.random.randint(1, 730))).isoformat(),
            'content_hash': content_hash
        }
        courses.append(course)
    
    # Generate interactions
    logger.info("Generating interactions...")
    interactions = []
    for i in range(50000):
        user = np.random.choice(users)
        course = np.random.choice(courses)
        interaction_type = np.random.choice(interaction_types)
        
        timestamp = datetime.now() - timedelta(days=np.random.randint(0, 365))
        duration = int(np.random.randint(0, 300)) if interaction_type in ['course_view', 'video_watch'] else 0
        completion_pct = float(min(1.0, duration / 300 + np.random.uniform(-0.1, 0.1))) if duration > 0 else 0.0
        
        rating = None
        if interaction_type == 'rate':
            rating = int(np.random.randint(1, 6))
        
        quiz_score = None
        if 'quiz' in interaction_type:
            if interaction_type == 'quiz_pass':
                quiz_score = float(np.random.uniform(0.7, 1.0))
            elif interaction_type == 'quiz_fail':
                quiz_score = float(np.random.uniform(0, 0.6))
            else:
                quiz_score = float(np.random.uniform(0, 1.0))
        
        interaction = {
            'interaction_id': f'INT_{i:08d}',
            'anonymized_user_id': user['anonymized_id'],
            'course_id': course['course_id'],
            'interaction_type': interaction_type,
            'timestamp': timestamp.isoformat(),
            'duration_seconds': duration,
            'completion_percentage': completion_pct,
            'rating': rating,
            'quiz_score': quiz_score,
            'device_type': user['device_type'],
            'session_id': f'SESSION_{np.random.randint(0, 10000):06d}',
            'location_hash': hashlib.sha256(f"{user['location_type']}_{np.random.randint(1, 100)}salt123".encode()).hexdigest()[:12] if np.random.random() > 0.7 else None
        }
        interactions.append(interaction)
    
    # Generate learning progress
    logger.info("Generating learning progress...")
    progress_records = []
    user_course_interactions = {}
    
    # Group interactions by user and course
    for interaction in interactions:
        key = (interaction['anonymized_user_id'], interaction['course_id'])
        if key not in user_course_interactions:
            user_course_interactions[key] = []
        user_course_interactions[key].append(interaction)
    
    # Create progress records
    for i, ((user_id, course_id), user_interactions) in enumerate(user_course_interactions.items()):
        user_interactions.sort(key=lambda x: x['timestamp'])
        
        start_date = user_interactions[0]['timestamp']
        last_accessed = user_interactions[-1]['timestamp']
        
        total_time = sum(i['duration_seconds'] for i in user_interactions)
        completion_percentages = [i['completion_percentage'] for i in user_interactions if i['completion_percentage'] > 0]
        max_completion = float(max(completion_percentages)) if completion_percentages else 0.0
        
        quiz_interactions = [i for i in user_interactions if i['quiz_score'] is not None]
        quiz_attempts = len(quiz_interactions)
        best_quiz_score = float(max([i['quiz_score'] for i in quiz_interactions])) if quiz_interactions else 0.0
        
        is_completed = any(i['interaction_type'] == 'course_complete' for i in user_interactions)
        completion_date = None
        if is_completed:
            complete_interactions = [i for i in user_interactions if i['interaction_type'] == 'course_complete']
            completion_date = complete_interactions[0]['timestamp'] if complete_interactions else None
        
        skill_points = int(max_completion * 100 + best_quiz_score * 50)
        if is_completed:
            skill_points += 100
        
        knowledge_gaps = []
        if best_quiz_score < 0.7:
            knowledge_gaps.append("quiz_performance")
        if max_completion < 0.8:
            knowledge_gaps.append("content_completion")
        if total_time < 60:
            knowledge_gaps.append("engagement_time")
        
        progress = {
            'progress_id': f'PROG_{i:08d}',
            'anonymized_user_id': user_id,
            'course_id': course_id,
            'start_date': start_date,
            'last_accessed': last_accessed,
            'completion_percentage': max_completion,
            'time_spent_seconds': total_time,
            'quiz_attempts': quiz_attempts,
            'best_quiz_score': best_quiz_score,
            'is_completed': is_completed,
            'completion_date': completion_date,
            'skill_points_earned': skill_points,
            'knowledge_gaps': knowledge_gaps
        }
        progress_records.append(progress)
    
    # Generate user preferences
    logger.info("Generating user preferences...")
    preferences = []
    user_interactions_dict = {}
    
    for interaction in interactions:
        if interaction['anonymized_user_id'] not in user_interactions_dict:
            user_interactions_dict[interaction['anonymized_user_id']] = []
        user_interactions_dict[interaction['anonymized_user_id']].append(interaction)
    
    for user in users:
        user_ints = user_interactions_dict.get(user['anonymized_id'], [])
        
        total_interactions = len(user_ints)
        if total_interactions == 0:
            continue
        
        video_interactions = len([i for i in user_ints if i['interaction_type'] == 'video_watch'])
        quiz_interactions = len([i for i in user_ints if 'quiz' in i['interaction_type']])
        
        preference = {
            'anonymized_user_id': user['anonymized_id'],
            'trade': user['trade'],
            'skill_level': user['skill_level'],
            'primary_language': user['primary_language'],
            'preferred_hour': np.random.randint(0, 24),
            'prefers_video': bool(video_interactions / total_interactions > 0.3),
            'prefers_quizzes': bool(quiz_interactions / total_interactions > 0.2),
            'avg_session_length': float(np.mean([i['duration_seconds'] for i in user_ints if i['duration_seconds'] > 0])) if user_ints else 0,
            'engagement_score': float(min(1.0, total_interactions / 50)),
            'completion_rate': float(len([i for i in user_ints if i['interaction_type'] == 'course_complete']) / max(1, len(set(i['course_id'] for i in user_ints)))),
            'device_preference': user['device_type'],
            'network_quality': user['network_quality']
        }
        preferences.append(preference)
    
    # Save all datasets
    logger.info("Saving datasets...")
    datasets = {
        'users.json': users,
        'courses.json': courses,
        'interactions.json': interactions,
        'learning_progress.json': progress_records,
        'user_preferences.json': preferences
    }
    
    for filename, data in datasets.items():
        filepath = output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(data)} records to {filepath}")
    
    # Save as CSV files
    try:
        pd.DataFrame(users).to_csv(output_dir / 'users.csv', index=False)
        pd.DataFrame(courses).to_csv(output_dir / 'courses.csv', index=False)
        pd.DataFrame(interactions).to_csv(output_dir / 'interactions.csv', index=False)
        pd.DataFrame(progress_records).to_csv(output_dir / 'learning_progress.csv', index=False)
        pd.DataFrame(preferences).to_csv(output_dir / 'user_preferences.csv', index=False)
        logger.info("Saved CSV versions of all datasets")
    except Exception as e:
        logger.warning(f"Could not save CSV files: {e}")
    
    # Create train/test splits
    logger.info("Creating train/test splits...")
    from sklearn.model_selection import train_test_split
    
    train_interactions, test_interactions = train_test_split(
        interactions, test_size=0.2, random_state=42
    )
    
    with open(output_dir / 'train_interactions.json', 'w') as f:
        json.dump(train_interactions, f, indent=2)
    
    with open(output_dir / 'test_interactions.json', 'w') as f:
        json.dump(test_interactions, f, indent=2)
    
    logger.info(f"Created train/test splits: {len(train_interactions)} train, {len(test_interactions)} test")
    
    # Generate summary
    summary = {
        'generation_date': datetime.now().isoformat(),
        'privacy_preserving': True,
        'anonymization_method': 'SHA256 hashing with salt',
        'datasets': {
            filename: {
                'record_count': len(data),
                'sample_fields': list(data[0].keys()) if data else []
            }
            for filename, data in datasets.items()
        }
    }
    
    with open(output_dir / 'dataset_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info("Dataset generation completed successfully!")

if __name__ == "__main__":
    generate_recommendation_data()