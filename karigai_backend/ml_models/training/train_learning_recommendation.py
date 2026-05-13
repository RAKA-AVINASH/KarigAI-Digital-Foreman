#!/usr/bin/env python3
"""
Learning Recommendation Model Training for KarigAI

This module implements collaborative filtering, content-based filtering, and hybrid
recommendation systems for personalized learning recommendations.

Task 19.2: Build learning recommendation model
- Implement collaborative filtering (matrix factorization) in PyTorch
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
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
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
    embedding_dim: int = 64
    learning_rate: float = 0.001
    weight_decay: float = 1e-5
    batch_size: int = 256
    epochs: int = 100
    
    # Content-based parameters
    content_embedding_dim: int = 128
    
    # Hybrid parameters
    alpha: float = 0.7  # Weight for collaborative filtering
    beta: float = 0.3   # Weight for content-based filtering
    
    # Training parameters
    device: str = 'cuda' if torch.cuda.is_available() else 'cpu'
    patience: int = 10
    min_delta: float = 1e-4


class InteractionDataset(Dataset):
    """Dataset for user-course interactions"""
    
    def __init__(self, interactions: pd.DataFrame, user_encoder: LabelEncoder, 
                 course_encoder: LabelEncoder):
        self.interactions = interactions
        self.user_encoder = user_encoder
        self.course_encoder = course_encoder
        
        # Encode users and courses
        self.user_ids = torch.LongTensor(
            self.user_encoder.transform(interactions['anonymized_user_id'])
        )
        self.course_ids = torch.LongTensor(
            self.course_encoder.transform(interactions['course_id'])
        )
        
        # Create ratings from interaction data
        self.ratings = self._create_ratings(interactions)
    
    def _create_ratings(self, interactions: pd.DataFrame) -> torch.FloatTensor:
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
            ratings.append(rating)
        
        return torch.FloatTensor(ratings)
    
    def __len__(self):
        return len(self.interactions)
    
    def __getitem__(self, idx):
        return {
            'user_id': self.user_ids[idx],
            'course_id': self.course_ids[idx],
            'rating': self.ratings[idx]
        }


class MatrixFactorizationModel(nn.Module):
    """Collaborative Filtering using Matrix Factorization"""
    
    def __init__(self, num_users: int, num_courses: int, embedding_dim: int = 64):
        super(MatrixFactorizationModel, self).__init__()
        
        self.num_users = num_users
        self.num_courses = num_courses
        self.embedding_dim = embedding_dim
        
        # User and course embeddings
        self.user_embedding = nn.Embedding(num_users, embedding_dim)
        self.course_embedding = nn.Embedding(num_courses, embedding_dim)
        
        # Bias terms
        self.user_bias = nn.Embedding(num_users, 1)
        self.course_bias = nn.Embedding(num_courses, 1)
        self.global_bias = nn.Parameter(torch.zeros(1))
        
        # Initialize embeddings
        nn.init.normal_(self.user_embedding.weight, std=0.1)
        nn.init.normal_(self.course_embedding.weight, std=0.1)
        nn.init.normal_(self.user_bias.weight, std=0.1)
        nn.init.normal_(self.course_bias.weight, std=0.1)
    
    def forward(self, user_ids: torch.Tensor, course_ids: torch.Tensor) -> torch.Tensor:
        # Get embeddings
        user_emb = self.user_embedding(user_ids)
        course_emb = self.course_embedding(course_ids)
        
        # Get biases
        user_b = self.user_bias(user_ids).squeeze()
        course_b = self.course_bias(course_ids).squeeze()
        
        # Compute dot product
        dot_product = (user_emb * course_emb).sum(dim=1)
        
        # Add biases
        prediction = dot_product + user_b + course_b + self.global_bias
        
        return prediction
    
    def get_user_embedding(self, user_id: int) -> torch.Tensor:
        """Get user embedding vector"""
        return self.user_embedding(torch.LongTensor([user_id]))
    
    def get_course_embedding(self, course_id: int) -> torch.Tensor:
        """Get course embedding vector"""
        return self.course_embedding(torch.LongTensor([course_id]))


class ContentBasedModel:
    """Content-based filtering using course features"""
    
    def __init__(self, courses: pd.DataFrame, config: RecommendationConfig):
        self.courses = courses
        self.config = config
        self.course_features = None
        self.similarity_matrix = None
        self.tfidf_vectorizer = None
        self.scaler = StandardScaler()
        
        self._build_course_features()
    
    def _build_course_features(self):
        """Build course feature matrix"""
        logger.info("Building course features for content-based filtering...")
        
        # Text features from title and topics
        text_features = []
        for _, course in self.courses.iterrows():
            text = f"{course['title']} {' '.join(course['topics'])}"
            text_features.append(text)
        
        # TF-IDF vectorization
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000, 
            stop_words='english',
            ngram_range=(1, 2)
        )
        tfidf_features = self.tfidf_vectorizer.fit_transform(text_features).toarray()
        
        # Categorical features
        categorical_features = []
        
        # Trade encoding
        trade_encoder = LabelEncoder()
        trade_encoded = trade_encoder.fit_transform(self.courses['trade'])
        trade_onehot = np.eye(len(trade_encoder.classes_))[trade_encoded]
        
        # Difficulty encoding
        difficulty_encoder = LabelEncoder()
        difficulty_encoded = difficulty_encoder.fit_transform(self.courses['difficulty'])
        difficulty_onehot = np.eye(len(difficulty_encoder.classes_))[difficulty_encoded]
        
        # Language encoding
        language_encoder = LabelEncoder()
        language_encoded = language_encoder.fit_transform(self.courses['language'])
        language_onehot = np.eye(len(language_encoder.classes_))[language_encoded]
        
        # Numerical features
        numerical_features = self.courses[[
            'duration_seconds', 'avg_rating', 'num_ratings', 'completion_rate'
        ]].fillna(0).values
        
        # Boolean features
        boolean_features = self.courses[[
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
        
        logger.info(f"Built course features with shape: {self.course_features.shape}")
    
    def get_similar_courses(self, course_id: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Get similar courses based on content"""
        try:
            course_idx = self.courses[self.courses['course_id'] == course_id].index[0]
            similarities = self.similarity_matrix[course_idx]
            
            # Get top-k similar courses (excluding self)
            similar_indices = np.argsort(similarities)[::-1][1:top_k+1]
            similar_courses = []
            
            for idx in similar_indices:
                similar_course_id = self.courses.iloc[idx]['course_id']
                similarity_score = similarities[idx]
                similar_courses.append((similar_course_id, similarity_score))
            
            return similar_courses
        except IndexError:
            return []
    
    def recommend_for_user(self, user_interactions: List[str], top_k: int = 10) -> List[Tuple[str, float]]:
        """Recommend courses based on user's interaction history"""
        if not user_interactions:
            return []
        
        # Get features for user's interacted courses
        user_course_features = []
        for course_id in user_interactions:
            try:
                course_idx = self.courses[self.courses['course_id'] == course_id].index[0]
                user_course_features.append(self.course_features[course_idx])
            except IndexError:
                continue
        
        if not user_course_features:
            return []
        
        # Create user profile as average of interacted course features
        user_profile = np.mean(user_course_features, axis=0)
        
        # Compute similarities with all courses
        similarities = cosine_similarity([user_profile], self.course_features)[0]
        
        # Get top-k recommendations (excluding already interacted courses)
        course_ids = self.courses['course_id'].tolist()
        recommendations = []
        
        for idx in np.argsort(similarities)[::-1]:
            course_id = course_ids[idx]
            if course_id not in user_interactions:
                recommendations.append((course_id, similarities[idx]))
                if len(recommendations) >= top_k:
                    break
        
        return recommendations


class KnowledgeGraphModel:
    """Knowledge gap identification using skill graphs"""
    
    def __init__(self, courses: pd.DataFrame, interactions: pd.DataFrame):
        self.courses = courses
        self.interactions = interactions
        self.skill_graph = self._build_skill_graph()
        self.user_skill_profiles = self._build_user_skill_profiles()
    
    def _build_skill_graph(self) -> Dict[str, Dict[str, float]]:
        """Build skill dependency graph from course prerequisites"""
        skill_graph = {}
        
        for _, course in self.courses.iterrows():
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
    
    def _build_user_skill_profiles(self) -> Dict[str, Dict[str, float]]:
        """Build user skill profiles from interaction history"""
        user_profiles = {}
        
        # Group interactions by user
        user_interactions = self.interactions.groupby('anonymized_user_id')
        
        for user_id, user_data in user_interactions:
            user_profiles[user_id] = {}
            
            # Calculate skill levels based on completed courses
            for _, interaction in user_data.iterrows():
                course_id = interaction['course_id']
                
                # Find course details
                course_info = self.courses[self.courses['course_id'] == course_id]
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


class SequentialRecommendationModel(nn.Module):
    """Sequential recommendation for learning paths using LSTM"""
    
    def __init__(self, num_courses: int, embedding_dim: int = 64, hidden_dim: int = 128):
        super(SequentialRecommendationModel, self).__init__()
        
        self.num_courses = num_courses
        self.embedding_dim = embedding_dim
        self.hidden_dim = hidden_dim
        
        # Course embedding
        self.course_embedding = nn.Embedding(num_courses, embedding_dim)
        
        # LSTM for sequence modeling
        self.lstm = nn.LSTM(embedding_dim, hidden_dim, batch_first=True)
        
        # Output layer
        self.output_layer = nn.Linear(hidden_dim, num_courses)
        
        # Dropout for regularization
        self.dropout = nn.Dropout(0.2)
    
    def forward(self, course_sequences: torch.Tensor) -> torch.Tensor:
        # Embed courses
        embedded = self.course_embedding(course_sequences)
        
        # LSTM forward pass
        lstm_out, _ = self.lstm(embedded)
        
        # Use last hidden state
        last_hidden = lstm_out[:, -1, :]
        
        # Apply dropout
        dropped = self.dropout(last_hidden)
        
        # Output layer
        output = self.output_layer(dropped)
        
        return output


class HybridRecommendationSystem:
    """Hybrid recommendation system combining multiple approaches"""
    
    def __init__(self, config: RecommendationConfig):
        self.config = config
        self.collaborative_model = None
        self.content_model = None
        self.knowledge_graph = None
        self.sequential_model = None
        
        # Encoders
        self.user_encoder = LabelEncoder()
        self.course_encoder = LabelEncoder()
        
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
    
    def prepare_encoders(self):
        """Prepare label encoders for users and courses"""
        # Fit encoders on all data (train + test)
        all_users = set(self.train_interactions_df['anonymized_user_id']) | \
                   set(self.test_interactions_df['anonymized_user_id'])
        all_courses = set(self.train_interactions_df['course_id']) | \
                     set(self.test_interactions_df['course_id'])
        
        self.user_encoder.fit(list(all_users))
        self.course_encoder.fit(list(all_courses))
        
        logger.info(f"Encoded {len(all_users)} users and {len(all_courses)} courses")
    
    def train_collaborative_filtering(self):
        """Train collaborative filtering model"""
        logger.info("Training collaborative filtering model...")
        
        # Create dataset
        train_dataset = InteractionDataset(
            self.train_interactions_df, 
            self.user_encoder, 
            self.course_encoder
        )
        
        train_loader = DataLoader(
            train_dataset, 
            batch_size=self.config.batch_size, 
            shuffle=True
        )
        
        # Initialize model
        num_users = len(self.user_encoder.classes_)
        num_courses = len(self.course_encoder.classes_)
        
        self.collaborative_model = MatrixFactorizationModel(
            num_users, num_courses, self.config.embedding_dim
        ).to(self.config.device)
        
        # Optimizer and loss
        optimizer = optim.Adam(
            self.collaborative_model.parameters(),
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay
        )
        criterion = nn.MSELoss()
        
        # Training loop
        best_loss = float('inf')
        patience_counter = 0
        
        for epoch in range(self.config.epochs):
            self.collaborative_model.train()
            total_loss = 0.0
            
            for batch in train_loader:
                user_ids = batch['user_id'].to(self.config.device)
                course_ids = batch['course_id'].to(self.config.device)
                ratings = batch['rating'].to(self.config.device)
                
                optimizer.zero_grad()
                predictions = self.collaborative_model(user_ids, course_ids)
                loss = criterion(predictions, ratings)
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item()
            
            avg_loss = total_loss / len(train_loader)
            
            if epoch % 10 == 0:
                logger.info(f"Epoch {epoch}, Loss: {avg_loss:.4f}")
            
            # Early stopping
            if avg_loss < best_loss - self.config.min_delta:
                best_loss = avg_loss
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= self.config.patience:
                    logger.info(f"Early stopping at epoch {epoch}")
                    break
        
        logger.info("Collaborative filtering training completed")
    
    def train_content_based(self):
        """Train content-based model"""
        logger.info("Training content-based model...")
        self.content_model = ContentBasedModel(self.courses_df, self.config)
        logger.info("Content-based model training completed")
    
    def train_knowledge_graph(self):
        """Build knowledge graph model"""
        logger.info("Building knowledge graph model...")
        self.knowledge_graph = KnowledgeGraphModel(
            self.courses_df, 
            self.train_interactions_df
        )
        logger.info("Knowledge graph model completed")
    
    def get_collaborative_recommendations(self, user_id: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Get recommendations from collaborative filtering"""
        if self.collaborative_model is None:
            return []
        
        try:
            user_idx = self.user_encoder.transform([user_id])[0]
        except ValueError:
            return []
        
        self.collaborative_model.eval()
        recommendations = []
        
        with torch.no_grad():
            user_tensor = torch.LongTensor([user_idx]).to(self.config.device)
            
            for course_idx in range(len(self.course_encoder.classes_)):
                course_tensor = torch.LongTensor([course_idx]).to(self.config.device)
                score = self.collaborative_model(user_tensor, course_tensor).item()
                course_id = self.course_encoder.inverse_transform([course_idx])[0]
                recommendations.append((course_id, score))
        
        # Sort by score and return top-k
        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations[:top_k]
    
    def get_content_recommendations(self, user_id: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Get recommendations from content-based filtering"""
        if self.content_model is None:
            return []
        
        # Get user's interaction history
        user_interactions = self.train_interactions_df[
            self.train_interactions_df['anonymized_user_id'] == user_id
        ]['course_id'].unique().tolist()
        
        return self.content_model.recommend_for_user(user_interactions, top_k)
    
    def get_hybrid_recommendations(self, user_id: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Get hybrid recommendations combining collaborative and content-based"""
        collab_recs = self.get_collaborative_recommendations(user_id, top_k * 2)
        content_recs = self.get_content_recommendations(user_id, top_k * 2)
        
        # Combine recommendations with weighted scores
        combined_scores = {}
        
        # Add collaborative filtering scores
        for course_id, score in collab_recs:
            combined_scores[course_id] = self.config.alpha * score
        
        # Add content-based scores
        for course_id, score in content_recs:
            if course_id in combined_scores:
                combined_scores[course_id] += self.config.beta * score
            else:
                combined_scores[course_id] = self.config.beta * score
        
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
        
        # Save collaborative filtering model
        if self.collaborative_model is not None:
            torch.save(
                self.collaborative_model.state_dict(),
                output_path / 'collaborative_model.pth'
            )
        
        # Save encoders
        with open(output_path / 'user_encoder.pkl', 'wb') as f:
            pickle.dump(self.user_encoder, f)
        
        with open(output_path / 'course_encoder.pkl', 'wb') as f:
            pickle.dump(self.course_encoder, f)
        
        # Save content model
        if self.content_model is not None:
            with open(output_path / 'content_model.pkl', 'wb') as f:
                pickle.dump(self.content_model, f)
        
        # Save knowledge graph
        if self.knowledge_graph is not None:
            with open(output_path / 'knowledge_graph.pkl', 'wb') as f:
                pickle.dump(self.knowledge_graph, f)
        
        # Save configuration and metrics
        config_dict = {
            'embedding_dim': self.config.embedding_dim,
            'learning_rate': self.config.learning_rate,
            'alpha': self.config.alpha,
            'beta': self.config.beta,
            'metrics': self.metrics
        }
        
        with open(output_path / 'model_config.json', 'w') as f:
            json.dump(config_dict, f, indent=2)
        
        logger.info(f"Models saved to {output_path}")
    
    def train_all_models(self):
        """Train all recommendation models"""
        logger.info("Starting training of all recommendation models...")
        
        # Prepare data
        self.prepare_encoders()
        
        # Train individual models
        self.train_collaborative_filtering()
        self.train_content_based()
        self.train_knowledge_graph()
        
        logger.info("All models trained successfully")


def main():
    """Main training function"""
    parser = argparse.ArgumentParser(description='Train learning recommendation models')
    parser.add_argument('--data-dir', default='./data/recommendation_datasets',
                        help='Directory containing recommendation datasets')
    parser.add_argument('--output-dir', default='./models/recommendation',
                        help='Output directory for trained models')
    parser.add_argument('--embedding-dim', type=int, default=64,
                        help='Embedding dimension for matrix factorization')
    parser.add_argument('--epochs', type=int, default=100,
                        help='Number of training epochs')
    parser.add_argument('--batch-size', type=int, default=256,
                        help='Batch size for training')
    parser.add_argument('--learning-rate', type=float, default=0.001,
                        help='Learning rate')
    
    args = parser.parse_args()
    
    # Create configuration
    config = RecommendationConfig(
        embedding_dim=args.embedding_dim,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate
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
    
    # Save models
    rec_system.save_model(args.output_dir)
    
    logger.info("Learning recommendation model training completed!")


if __name__ == "__main__":
    main()