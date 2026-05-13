#!/usr/bin/env python3
"""
Learning Recommendation Model Training for KarigAI (Scikit-learn version)

This module implements collaborative filtering, content-based filtering, and hybrid
recommendation systems using scikit-learn and traditional ML approaches.

Task 19.2: Build learning recommendation model
- Implement collaborative filtering (matrix factorization) using scikit-learn
- Add content-based filtering using course embeddings
- Implement hybrid recommendation system
- Add knowledge gap identification using skill graphs
- Create sequential recommendation for learning paths
- Validate on test set (target: >0.75 NDCG@10)
"""

import os
import json
import numpy as np
import pandas as pd
from sklearn.decomposition import NMF, TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import LabelEncoder, StandardScaler, MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.neighbors import NearestNeighbors
from sklearn.cluster import KMeans
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import pickle
import argparse
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RecommendationConfig:
    """Configuration for recommendation models"""
    # Matrix Factorization parameters
    n_components: int = 50
    max_iter: int = 200
    random_state: int = 42
    
    # Content-based parameters
    max_features: int = 1000
    
    # Hybrid parameters
    alpha: float = 0.7  # Weight for collaborative filtering
    beta: float = 0.3   # Weight for content-based filtering
    
    # Evaluation parameters
    top_k: int = 10


class CollaborativeFilteringModel:
    """Collaborative Filtering using Non-negative Matrix Factorization"""
    
    def __init__(self, config: RecommendationConfig):
        self.config = config
        self.model = NMF(
            n_components=config.n_components,
            max_iter=config.max_iter,
            random_state=config.random_state
        )
        self.user_encoder = LabelEncoder()
        self.course_encoder = LabelEncoder()
        self.user_item_matrix = None
        self.user_features = None
        self.item_features = None
        self.mean_rating = 0.0
    
    def _create_ratings(self, interactions: pd.DataFrame) -> pd.DataFrame:
        """Create implicit ratings from interaction data"""
        ratings = []
        
        for _, row in interactions.iterrows():
            # Create implicit rating based on interaction type and completion
            rating = 0.0
            
            if row['interaction_type'] == 'course_complete':
                rating = 5.0
            elif row['interaction_type'] == 'quiz_pass':
                rating = 4.5
            elif row['interaction_type'] == 'course_start':
                rating = 3.0 + row['completion_percentage'] * 2.0
            elif row['interaction_type'] == 'video_watch':
                rating = 2.0 + row['completion_percentage'] * 2.0
            elif row['interaction_type'] == 'course_view':
                rating = 1.0 + row['completion_percentage'] * 1.0
            elif row['interaction_type'] == 'bookmark':
                rating = 3.5
            elif row['interaction_type'] == 'rate' and row['rating'] is not None:
                rating = float(row['rating'])
            else:
                rating = 1.0
            
            # Adjust based on quiz performance
            if row['quiz_score'] is not None:
                rating += row['quiz_score'] * 1.0
            
            # Normalize to 0-5 scale
            rating = max(0.0, min(5.0, rating))
            ratings.append({
                'user_id': row['anonymized_user_id'],
                'course_id': row['course_id'],
                'rating': rating
            })
        
        return pd.DataFrame(ratings)
    
    def fit(self, interactions: pd.DataFrame):
        """Train the collaborative filtering model"""
        logger.info("Training collaborative filtering model...")
        
        # Create ratings
        ratings_df = self._create_ratings(interactions)
        
        # Encode users and courses
        all_users = ratings_df['user_id'].unique()
        all_courses = ratings_df['course_id'].unique()
        
        self.user_encoder.fit(all_users)
        self.course_encoder.fit(all_courses)
        
        # Create user-item matrix
        n_users = len(all_users)
        n_courses = len(all_courses)
        
        self.user_item_matrix = np.zeros((n_users, n_courses))
        
        for _, row in ratings_df.iterrows():
            user_idx = self.user_encoder.transform([row['user_id']])[0]
            course_idx = self.course_encoder.transform([row['course_id']])[0]
            self.user_item_matrix[user_idx, course_idx] = row['rating']
        
        # Calculate mean rating for handling missing values
        self.mean_rating = np.mean(self.user_item_matrix[self.user_item_matrix > 0])
        
        # Train NMF model
        self.model.fit(self.user_item_matrix)
        
        # Get user and item features
        self.user_features = self.model.transform(self.user_item_matrix)
        self.item_features = self.model.components_.T
        
        logger.info(f"Collaborative filtering model trained with {n_users} users and {n_courses} courses")
    
    def predict(self, user_id: str, course_id: str) -> float:
        """Predict rating for user-course pair"""
        try:
            user_idx = self.user_encoder.transform([user_id])[0]
            course_idx = self.course_encoder.transform([course_id])[0]
            
            # Reconstruct rating using matrix factorization
            predicted_rating = np.dot(self.user_features[user_idx], self.item_features[course_idx])
            return max(0.0, min(5.0, predicted_rating))
        except (ValueError, IndexError):
            return self.mean_rating
    
    def recommend(self, user_id: str, top_k: int = 10, exclude_seen: bool = True) -> List[Tuple[str, float]]:
        """Get top-k recommendations for a user"""
        try:
            user_idx = self.user_encoder.transform([user_id])[0]
        except ValueError:
            return []
        
        # Get all course predictions for this user
        user_vector = self.user_features[user_idx]
        scores = np.dot(user_vector, self.item_features.T)
        
        # Get course IDs and scores
        recommendations = []
        for course_idx, score in enumerate(scores):
            course_id = self.course_encoder.inverse_transform([course_idx])[0]
            
            # Exclude already seen courses if requested
            if exclude_seen and self.user_item_matrix[user_idx, course_idx] > 0:
                continue
            
            recommendations.append((course_id, float(score)))
        
        # Sort by score and return top-k
        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations[:top_k]


class ContentBasedModel:
    """Content-based filtering using course features"""
    
    def __init__(self, config: RecommendationConfig):
        self.config = config
        self.courses_df = None
        self.course_features = None
        self.similarity_matrix = None
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=config.max_features,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.scaler = StandardScaler()
        self.course_to_idx = {}
    
    def fit(self, courses: pd.DataFrame):
        """Train the content-based model"""
        logger.info("Training content-based model...")
        
        self.courses_df = courses.copy()
        self._build_course_features()
        
        logger.info(f"Content-based model trained with {len(courses)} courses")
    
    def _build_course_features(self):
        """Build course feature matrix"""
        # Text features from title and topics
        text_features = []
        for _, course in self.courses_df.iterrows():
            text = f"{course['title']} {' '.join(course['topics'])}"
            text_features.append(text)
        
        # TF-IDF vectorization
        tfidf_features = self.tfidf_vectorizer.fit_transform(text_features).toarray()
        
        # Categorical features
        # Trade encoding
        trade_encoder = LabelEncoder()
        trade_encoded = trade_encoder.fit_transform(self.courses_df['trade'])
        trade_onehot = np.eye(len(trade_encoder.classes_))[trade_encoded]
        
        # Difficulty encoding
        difficulty_encoder = LabelEncoder()
        difficulty_encoded = difficulty_encoder.fit_transform(self.courses_df['difficulty'])
        difficulty_onehot = np.eye(len(difficulty_encoder.classes_))[difficulty_encoded]
        
        # Language encoding
        language_encoder = LabelEncoder()
        language_encoded = language_encoder.fit_transform(self.courses_df['language'])
        language_onehot = np.eye(len(language_encoder.classes_))[language_encoded]
        
        # Numerical features
        numerical_features = self.courses_df[[
            'duration_seconds', 'avg_rating', 'num_ratings', 'completion_rate'
        ]].fillna(0).values
        
        # Boolean features
        boolean_features = self.courses_df[[
            'has_video', 'has_quiz', 'has_practical'
        ]].astype(int).values
        
        # Combine all features
        self.course_features = np.hstack([
            tfidf_features,
            trade_onehot,
            difficulty_onehot,
            language_onehot,
            self.scaler.fit_transform(numerical_features),
            boolean_features
        ])
        
        # Compute similarity matrix
        self.similarity_matrix = cosine_similarity(self.course_features)
        
        # Create course to index mapping
        self.course_to_idx = {
            course_id: idx for idx, course_id in enumerate(self.courses_df['course_id'])
        }
    
    def get_similar_courses(self, course_id: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Get similar courses based on content"""
        if course_id not in self.course_to_idx:
            return []
        
        course_idx = self.course_to_idx[course_id]
        similarities = self.similarity_matrix[course_idx]
        
        # Get top-k similar courses (excluding self)
        similar_indices = np.argsort(similarities)[::-1][1:top_k+1]
        similar_courses = []
        
        for idx in similar_indices:
            similar_course_id = self.courses_df.iloc[idx]['course_id']
            similarity_score = similarities[idx]
            similar_courses.append((similar_course_id, float(similarity_score)))
        
        return similar_courses
    
    def recommend_for_user(self, user_interactions: List[str], top_k: int = 10) -> List[Tuple[str, float]]:
        """Recommend courses based on user's interaction history"""
        if not user_interactions:
            return []
        
        # Get features for user's interacted courses
        user_course_features = []
        for course_id in user_interactions:
            if course_id in self.course_to_idx:
                course_idx = self.course_to_idx[course_id]
                user_course_features.append(self.course_features[course_idx])
        
        if not user_course_features:
            return []
        
        # Create user profile as average of interacted course features
        user_profile = np.mean(user_course_features, axis=0)
        
        # Compute similarities with all courses
        similarities = cosine_similarity([user_profile], self.course_features)[0]
        
        # Get top-k recommendations (excluding already interacted courses)
        recommendations = []
        
        for idx in np.argsort(similarities)[::-1]:
            course_id = self.courses_df.iloc[idx]['course_id']
            if course_id not in user_interactions:
                recommendations.append((course_id, float(similarities[idx])))
                if len(recommendations) >= top_k:
                    break
        
        return recommendations


class KnowledgeGraphModel:
    """Knowledge gap identification using skill graphs"""
    
    def __init__(self):
        self.skill_graph = {}
        self.user_skill_profiles = {}
        self.courses_df = None
    
    def fit(self, courses: pd.DataFrame, interactions: pd.DataFrame):
        """Build knowledge graph from courses and interactions"""
        logger.info("Building knowledge graph model...")
        
        self.courses_df = courses
        self.skill_graph = self._build_skill_graph(courses)
        self.user_skill_profiles = self._build_user_skill_profiles(courses, interactions)
        
        logger.info(f"Knowledge graph built with {len(self.skill_graph)} skills")
    
    def _build_skill_graph(self, courses: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """Build skill dependency graph from course prerequisites"""
        skill_graph = {}
        
        for _, course in courses.iterrows():
            course_id = course['course_id']
            topics = course['topics']
            difficulty = course['difficulty']
            
            # Create skill nodes
            for topic in topics:
                if topic not in skill_graph:
                    skill_graph[topic] = {}
                
                # Add course to skill
                skill_graph[topic][course_id] = self._difficulty_to_weight(difficulty)
        
        return skill_graph
    
    def _difficulty_to_weight(self, difficulty: str) -> float:
        """Convert difficulty level to weight"""
        weights = {
            'beginner': 1.0,
            'intermediate': 2.0,
            'advanced': 3.0,
            'expert': 4.0
        }
        return weights.get(difficulty, 1.0)
    
    def _build_user_skill_profiles(self, courses: pd.DataFrame, 
                                   interactions: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """Build user skill profiles from interaction history"""
        user_profiles = {}
        
        # Group interactions by user
        user_interactions = interactions.groupby('anonymized_user_id')
        
        for user_id, user_data in user_interactions:
            user_profiles[user_id] = {}
            
            # Calculate skill levels based on completed courses
            for _, interaction in user_data.iterrows():
                course_id = interaction['course_id']
                
                # Find course details
                course_info = courses[courses['course_id'] == course_id]
                if course_info.empty:
                    continue
                
                course_info = course_info.iloc[0]
                topics = course_info['topics']
                difficulty_weight = self._difficulty_to_weight(course_info['difficulty'])
                
                # Update skill levels based on interaction type
                skill_gain = self._calculate_skill_gain(interaction, difficulty_weight)
                
                for topic in topics:
                    if topic not in user_profiles[user_id]:
                        user_profiles[user_id][topic] = 0.0
                    user_profiles[user_id][topic] += skill_gain
        
        return user_profiles
    
    def _calculate_skill_gain(self, interaction: pd.Series, difficulty_weight: float) -> float:
        """Calculate skill gain from interaction"""
        base_gain = 0.0
        
        if interaction['interaction_type'] == 'course_complete':
            base_gain = 1.0
        elif interaction['interaction_type'] == 'quiz_pass':
            base_gain = 0.8
        elif interaction['interaction_type'] == 'course_start':
            base_gain = 0.3 * interaction['completion_percentage']
        elif interaction['interaction_type'] == 'video_watch':
            base_gain = 0.2 * interaction['completion_percentage']
        
        # Adjust by quiz performance
        if interaction['quiz_score'] is not None:
            base_gain *= (0.5 + 0.5 * interaction['quiz_score'])
        
        return base_gain * difficulty_weight
    
    def identify_knowledge_gaps(self, user_id: str, target_skill: str) -> List[str]:
        """Identify knowledge gaps for a user in a target skill"""
        if user_id not in self.user_skill_profiles:
            return []
        
        user_skills = self.user_skill_profiles[user_id]
        current_level = user_skills.get(target_skill, 0.0)
        
        # Find courses that could help bridge the gap
        gap_courses = []
        
        if target_skill in self.skill_graph:
            for course_id, required_level in self.skill_graph[target_skill].items():
                if required_level > current_level:
                    gap_courses.append(course_id)
        
        return gap_courses
    
    def get_skill_recommendations(self, user_id: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Get recommendations based on skill gaps"""
        if user_id not in self.user_skill_profiles:
            return []
        
        user_skills = self.user_skill_profiles[user_id]
        recommendations = []
        
        # Find skills with low proficiency
        for skill, level in user_skills.items():
            if level < 2.0:  # Threshold for skill gap
                gap_courses = self.identify_knowledge_gaps(user_id, skill)
                for course_id in gap_courses:
                    gap_score = 2.0 - level  # Higher score for bigger gaps
                    recommendations.append((course_id, gap_score))
        
        # Sort by gap score and return top-k
        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations[:top_k]


class SequentialRecommendationModel:
    """Sequential recommendation for learning paths"""
    
    def __init__(self, config: RecommendationConfig):
        self.config = config
        self.user_sequences = {}
        self.course_transitions = {}
        self.courses_df = None
    
    def fit(self, courses: pd.DataFrame, interactions: pd.DataFrame):
        """Build sequential patterns from user interactions"""
        logger.info("Building sequential recommendation model...")
        
        self.courses_df = courses
        self._build_user_sequences(interactions)
        self._build_transition_matrix()
        
        logger.info("Sequential recommendation model built")
    
    def _build_user_sequences(self, interactions: pd.DataFrame):
        """Build user course sequences from interactions"""
        # Group by user and sort by timestamp
        user_interactions = interactions.groupby('anonymized_user_id')
        
        for user_id, user_data in user_interactions:
            # Sort by timestamp
            user_data = user_data.sort_values('timestamp')
            
            # Extract course sequence
            sequence = []
            for _, interaction in user_data.iterrows():
                if interaction['interaction_type'] in ['course_start', 'course_complete']:
                    sequence.append(interaction['course_id'])
            
            if len(sequence) > 1:
                self.user_sequences[user_id] = sequence
    
    def _build_transition_matrix(self):
        """Build course transition probabilities"""
        transitions = {}
        
        for user_id, sequence in self.user_sequences.items():
            for i in range(len(sequence) - 1):
                current_course = sequence[i]
                next_course = sequence[i + 1]
                
                if current_course not in transitions:
                    transitions[current_course] = {}
                
                if next_course not in transitions[current_course]:
                    transitions[current_course][next_course] = 0
                
                transitions[current_course][next_course] += 1
        
        # Convert counts to probabilities
        for current_course in transitions:
            total_transitions = sum(transitions[current_course].values())
            for next_course in transitions[current_course]:
                transitions[current_course][next_course] /= total_transitions
        
        self.course_transitions = transitions
    
    def get_next_course_recommendations(self, last_course: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Get next course recommendations based on sequential patterns"""
        if last_course not in self.course_transitions:
            return []
        
        # Get transition probabilities
        transitions = self.course_transitions[last_course]
        
        # Sort by probability and return top-k
        recommendations = [(course, prob) for course, prob in transitions.items()]
        recommendations.sort(key=lambda x: x[1], reverse=True)
        
        return recommendations[:top_k]


class HybridRecommendationSystem:
    """Hybrid recommendation system combining multiple approaches"""
    
    def __init__(self, config: RecommendationConfig):
        self.config = config
        self.collaborative_model = CollaborativeFilteringModel(config)
        self.content_model = ContentBasedModel(config)
        self.knowledge_graph = KnowledgeGraphModel()
        self.sequential_model = SequentialRecommendationModel(config)
        
        # Data
        self.users_df = None
        self.courses_df = None
        self.train_interactions_df = None
        self.test_interactions_df = None
        
        # Evaluation metrics
        self.metrics = {}
    
    def load_data(self, data_dir: str):
        """Load training data"""
        logger.info("Loading recommendation data...")
        
        # Load datasets
        with open(f"{data_dir}/users.json", 'r') as f:
            users_data = json.load(f)
        
        with open(f"{data_dir}/courses.json", 'r') as f:
            courses_data = json.load(f)
        
        with open(f"{data_dir}/train_interactions.json", 'r') as f:
            train_interactions = json.load(f)
        
        with open(f"{data_dir}/test_interactions.json", 'r') as f:
            test_interactions = json.load(f)
        
        # Convert to DataFrames
        self.users_df = pd.DataFrame(users_data)
        self.courses_df = pd.DataFrame(courses_data)
        self.train_interactions_df = pd.DataFrame(train_interactions)
        self.test_interactions_df = pd.DataFrame(test_interactions)
        
        logger.info(f"Loaded {len(self.users_df)} users, {len(self.courses_df)} courses")
        logger.info(f"Train interactions: {len(self.train_interactions_df)}")
        logger.info(f"Test interactions: {len(self.test_interactions_df)}")
    
    def train_all_models(self):
        """Train all recommendation models"""
        logger.info("Starting training of all recommendation models...")
        
        # Train individual models
        self.collaborative_model.fit(self.train_interactions_df)
        self.content_model.fit(self.courses_df)
        self.knowledge_graph.fit(self.courses_df, self.train_interactions_df)
        self.sequential_model.fit(self.courses_df, self.train_interactions_df)
        
        logger.info("All models trained successfully")
    
    def get_hybrid_recommendations(self, user_id: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Get hybrid recommendations combining all approaches"""
        # Get recommendations from each model
        collab_recs = self.collaborative_model.recommend(user_id, top_k * 2)
        
        # Get user's interaction history for content-based
        user_interactions = self.train_interactions_df[
            self.train_interactions_df['anonymized_user_id'] == user_id
        ]['course_id'].unique().tolist()
        
        content_recs = self.content_model.recommend_for_user(user_interactions, top_k * 2)
        skill_recs = self.knowledge_graph.get_skill_recommendations(user_id, top_k)
        
        # Get last course for sequential recommendations
        if user_interactions:
            last_course = user_interactions[-1]
            seq_recs = self.sequential_model.get_next_course_recommendations(last_course, top_k)
        else:
            seq_recs = []
        
        # Combine recommendations with weighted scores
        combined_scores = {}
        
        # Add collaborative filtering scores (weight: alpha)
        for course_id, score in collab_recs:
            combined_scores[course_id] = self.config.alpha * score
        
        # Add content-based scores (weight: beta)
        for course_id, score in content_recs:
            if course_id in combined_scores:
                combined_scores[course_id] += self.config.beta * score
            else:
                combined_scores[course_id] = self.config.beta * score
        
        # Add skill-based scores (weight: 0.2)
        for course_id, score in skill_recs:
            if course_id in combined_scores:
                combined_scores[course_id] += 0.2 * score
            else:
                combined_scores[course_id] = 0.2 * score
        
        # Add sequential scores (weight: 0.1)
        for course_id, score in seq_recs:
            if course_id in combined_scores:
                combined_scores[course_id] += 0.1 * score
            else:
                combined_scores[course_id] = 0.1 * score
        
        # Sort and return top-k
        recommendations = [(course_id, score) for course_id, score in combined_scores.items()]
        recommendations.sort(key=lambda x: x[1], reverse=True)
        
        return recommendations[:top_k]
    
    def calculate_ndcg(self, recommendations: List[Tuple[str, float]], 
                      relevant_courses: List[str], k: int = 10) -> float:
        """Calculate NDCG@k metric"""
        if not recommendations or not relevant_courses:
            return 0.0
        
        # Get top-k recommendations
        top_k_recs = [course_id for course_id, _ in recommendations[:k]]
        
        # Calculate DCG
        dcg = 0.0
        for i, course_id in enumerate(top_k_recs):
            if course_id in relevant_courses:
                dcg += 1.0 / np.log2(i + 2)  # +2 because log2(1) = 0
        
        # Calculate IDCG (ideal DCG)
        idcg = 0.0
        for i in range(min(len(relevant_courses), k)):
            idcg += 1.0 / np.log2(i + 2)
        
        # Return NDCG
        return dcg / idcg if idcg > 0 else 0.0
    
    def evaluate_model(self):
        """Evaluate the recommendation system"""
        logger.info("Evaluating recommendation system...")
        
        # Group test interactions by user
        test_users = self.test_interactions_df.groupby('anonymized_user_id')
        
        ndcg_scores = []
        precision_scores = []
        recall_scores = []
        
        for user_id, user_test_data in test_users:
            # Get relevant courses (courses the user interacted with in test set)
            relevant_courses = user_test_data['course_id'].unique().tolist()
            
            # Get recommendations
            recommendations = self.get_hybrid_recommendations(user_id, 10)
            
            if not recommendations:
                continue
            
            # Calculate metrics
            ndcg = self.calculate_ndcg(recommendations, relevant_courses, 10)
            ndcg_scores.append(ndcg)
            
            # Precision@10
            recommended_courses = [course_id for course_id, _ in recommendations[:10]]
            precision = len(set(recommended_courses) & set(relevant_courses)) / len(recommended_courses)
            precision_scores.append(precision)
            
            # Recall@10
            recall = len(set(recommended_courses) & set(relevant_courses)) / len(relevant_courses)
            recall_scores.append(recall)
        
        # Calculate average metrics
        avg_ndcg = np.mean(ndcg_scores) if ndcg_scores else 0.0
        avg_precision = np.mean(precision_scores) if precision_scores else 0.0
        avg_recall = np.mean(recall_scores) if recall_scores else 0.0
        
        self.metrics = {
            'ndcg_10': avg_ndcg,
            'precision_10': avg_precision,
            'recall_10': avg_recall,
            'num_evaluated_users': len(ndcg_scores)
        }
        
        logger.info(f"Evaluation Results:")
        logger.info(f"NDCG@10: {avg_ndcg:.4f}")
        logger.info(f"Precision@10: {avg_precision:.4f}")
        logger.info(f"Recall@10: {avg_recall:.4f}")
        logger.info(f"Evaluated users: {len(ndcg_scores)}")
        
        return self.metrics
    
    def save_model(self, output_dir: str):
        """Save trained models"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save all models
        models = {
            'collaborative_model': self.collaborative_model,
            'content_model': self.content_model,
            'knowledge_graph': self.knowledge_graph,
            'sequential_model': self.sequential_model
        }
        
        for model_name, model in models.items():
            with open(output_path / f'{model_name}.pkl', 'wb') as f:
                pickle.dump(model, f)
        
        # Save configuration and metrics
        config_dict = {
            'n_components': self.config.n_components,
            'max_features': self.config.max_features,
            'alpha': self.config.alpha,
            'beta': self.config.beta,
            'metrics': self.metrics
        }
        
        with open(output_path / 'model_config.json', 'w') as f:
            json.dump(config_dict, f, indent=2)
        
        logger.info(f"Models saved to {output_path}")


def main():
    """Main training function"""
    parser = argparse.ArgumentParser(description='Train learning recommendation models')
    parser.add_argument('--data-dir', default='./data/recommendation_datasets',
                        help='Directory containing recommendation datasets')
    parser.add_argument('--output-dir', default='./models/recommendation',
                        help='Output directory for trained models')
    parser.add_argument('--n-components', type=int, default=50,
                        help='Number of components for matrix factorization')
    parser.add_argument('--max-features', type=int, default=1000,
                        help='Maximum features for TF-IDF')
    parser.add_argument('--alpha', type=float, default=0.7,
                        help='Weight for collaborative filtering')
    parser.add_argument('--beta', type=float, default=0.3,
                        help='Weight for content-based filtering')
    
    args = parser.parse_args()
    
    # Create configuration
    config = RecommendationConfig(
        n_components=args.n_components,
        max_features=args.max_features,
        alpha=args.alpha,
        beta=args.beta
    )
    
    # Initialize recommendation system
    rec_system = HybridRecommendationSystem(config)
    
    # Load data
    rec_system.load_data(args.data_dir)
    
    # Train models
    rec_system.train_all_models()
    
    # Evaluate
    metrics = rec_system.evaluate_model()
    
    # Check if target NDCG@10 > 0.75 is achieved
    if metrics['ndcg_10'] >= 0.75:
        logger.info(f"✅ Target NDCG@10 achieved: {metrics['ndcg_10']:.4f} >= 0.75")
    else:
        logger.warning(f"❌ Target NDCG@10 not achieved: {metrics['ndcg_10']:.4f} < 0.75")
        logger.info("Consider tuning hyperparameters or adding more training data")
    
    # Save models
    rec_system.save_model(args.output_dir)
    
    logger.info("Learning recommendation model training completed!")


if __name__ == "__main__":
    main()