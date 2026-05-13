"""
NLP Dataset Preparation Utilities for KarigAI

This module provides utilities for collecting, cleaning, and preparing NLP datasets
for intent recognition, translation, knowledge retrieval, and scheme matching.
"""

import os
import json
import re
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IntentDatasetPreparator:
    """Prepare intent recognition datasets"""
    
    INTENT_CLASSES = [
        'invoice_generation',
        'repair_query',
        'equipment_identification',
        'quality_assessment',
        'learning_request',
        'document_request',
        'general_query',
        'complaint',
        'feedback'
    ]
    
    ENTITY_TYPES = [
        'amount',
        'date',
        'item',
        'equipment',
        'location',
        'person_name',
        'phone_number'
    ]
    
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def create_synthetic_examples(self, num_examples: int = 1000) -> List[Dict]:
        """Create synthetic training examples for intent recognition"""
        examples = []
        
        # Templates for each intent class
        templates = {
            'invoice_generation': [
                "मुझे एक बिल बनाना है {amount} रुपये का",
                "I need to create an invoice for {amount} rupees",
                "Generate bill for {item} worth {amount}",
                "{customer} के लिए बिल बनाओ {amount} का"
            ],
            'repair_query': [
                "मेरा {equipment} काम नहीं कर रहा",
                "How to fix {equipment} error code {error_code}",
                "{equipment} में क्या problem है",
                "Troubleshoot {equipment} not working"
            ],
            'equipment_identification': [
                "यह कौन सा {equipment} है",
                "Identify this equipment",
                "What brand is this {equipment}",
                "Tell me about this machine"
            ],
            'quality_assessment': [
                "इस {item} की quality कैसी है",
                "Grade this {item}",
                "What is the quality of this product",
                "Check {item} quality"
            ],
            'learning_request': [
                "मुझे {skill} सीखना है",
                "Teach me how to {skill}",
                "I want to learn {skill}",
                "Show me tutorial for {skill}"
            ],
            'document_request': [
                "मुझे {document_type} चाहिए",
                "Generate {document_type}",
                "Create {document_type} for me",
                "I need {document_type}"
            ],
            'general_query': [
                "यह कैसे काम करता है",
                "What is {topic}",
                "Tell me about {topic}",
                "Explain {topic}"
            ],
            'complaint': [
                "यह service अच्छी नहीं है",
                "I am not satisfied with {service}",
                "Problem with {service}",
                "Complaint about {service}"
            ],
            'feedback': [
                "बहुत अच्छा app है",
                "Great service",
                "Thank you for helping",
                "Excellent experience"
            ]
        }
        
        # Entity values for substitution
        entity_values = {
            'amount': ['500', '1000', '2500', '5000', '10000'],
            'item': ['fan', 'AC', 'refrigerator', 'washing machine', 'TV'],
            'equipment': ['mixer', 'grinder', 'motor', 'pump', 'heater'],
            'error_code': ['E01', 'E02', 'F1', 'F2', 'ERR-123'],
            'customer': ['राम', 'श्याम', 'Mr. Kumar', 'Mrs. Sharma'],
            'skill': ['welding', 'plumbing', 'electrical work', 'carpentry'],
            'document_type': ['invoice', 'receipt', 'contract', 'report'],
            'topic': ['safety', 'warranty', 'installation', 'maintenance'],
            'service': ['delivery', 'support', 'repair', 'installation']
        }
        
        for intent, template_list in templates.items():
            for _ in range(num_examples // len(templates)):
                template = np.random.choice(template_list)
                
                # Replace placeholders with random entity values
                text = template
                entities = []
                for entity_type, values in entity_values.items():
                    if f'{{{entity_type}}}' in text:
                        value = np.random.choice(values)
                        start_idx = text.find(f'{{{entity_type}}}')
                        text = text.replace(f'{{{entity_type}}}', value, 1)
                        entities.append({
                            'type': entity_type,
                            'value': value,
                            'start': start_idx,
                            'end': start_idx + len(value)
                        })
                
                examples.append({
                    'text': text,
                    'intent': intent,
                    'entities': entities,
                    'language': 'hi' if any(ord(c) > 127 for c in text) else 'en'
                })
        
        return examples
    
    def save_dataset(self, examples: List[Dict], split: str = 'train'):
        """Save dataset to JSON file"""
        output_file = self.output_dir / f'intent_{split}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(examples, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(examples)} examples to {output_file}")
    
    def prepare_datasets(self, num_examples: int = 10000):
        """Prepare train/val/test splits"""
        logger.info("Creating synthetic intent recognition examples...")
        examples = self.create_synthetic_examples(num_examples)
        
        # Split into train/val/test (80/10/10)
        train_examples, temp_examples = train_test_split(
            examples, test_size=0.2, random_state=42, stratify=[e['intent'] for e in examples]
        )
        val_examples, test_examples = train_test_split(
            temp_examples, test_size=0.5, random_state=42, stratify=[e['intent'] for e in temp_examples]
        )
        
        self.save_dataset(train_examples, 'train')
        self.save_dataset(val_examples, 'val')
        self.save_dataset(test_examples, 'test')
        
        logger.info(f"Dataset split: Train={len(train_examples)}, Val={len(val_examples)}, Test={len(test_examples)}")


class TranslationDatasetPreparator:
    """Prepare translation datasets"""
    
    SUPPORTED_LANGUAGES = ['hi', 'en', 'ml', 'pa', 'bn', 'ta', 'te', 'doi']
    
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def create_synthetic_pairs(self, num_pairs: int = 1000) -> List[Dict]:
        """Create synthetic translation pairs"""
        pairs = []
        
        # Sample parallel sentences (Hindi-English)
        sample_pairs = [
            ("मुझे मदद चाहिए", "I need help"),
            ("यह कैसे काम करता है", "How does this work"),
            ("बिल बनाओ", "Create invoice"),
            ("मशीन ठीक करो", "Fix the machine"),
            ("गुणवत्ता जांचो", "Check quality"),
            ("मुझे सीखना है", "I want to learn"),
            ("धन्यवाद", "Thank you"),
            ("समस्या है", "There is a problem"),
            ("कीमत क्या है", "What is the price"),
            ("यह अच्छा है", "This is good")
        ]
        
        # Augment with variations
        for _ in range(num_pairs):
            hi_text, en_text = sample_pairs[np.random.randint(len(sample_pairs))]
            
            pairs.append({
                'source': hi_text,
                'target': en_text,
                'source_lang': 'hi',
                'target_lang': 'en',
                'register': np.random.choice(['colloquial', 'formal', 'technical'])
            })
        
        return pairs
    
    def save_dataset(self, pairs: List[Dict], split: str = 'train'):
        """Save translation dataset"""
        output_file = self.output_dir / f'translation_{split}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(pairs, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(pairs)} translation pairs to {output_file}")
    
    def prepare_datasets(self, num_pairs: int = 50000):
        """Prepare translation datasets"""
        logger.info("Creating synthetic translation pairs...")
        pairs = self.create_synthetic_pairs(num_pairs)
        
        # Split into train/val/test (80/10/10)
        train_pairs, temp_pairs = train_test_split(pairs, test_size=0.2, random_state=42)
        val_pairs, test_pairs = train_test_split(temp_pairs, test_size=0.5, random_state=42)
        
        self.save_dataset(train_pairs, 'train')
        self.save_dataset(val_pairs, 'val')
        self.save_dataset(test_pairs, 'test')
        
        logger.info(f"Dataset split: Train={len(train_pairs)}, Val={len(val_pairs)}, Test={len(test_pairs)}")


class KnowledgeDatasetPreparator:
    """Prepare knowledge retrieval datasets"""
    
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def create_synthetic_qa_pairs(self, num_pairs: int = 1000) -> List[Dict]:
        """Create synthetic question-answer pairs"""
        qa_pairs = []
        
        # Sample QA templates
        templates = [
            {
                'question': 'How to fix {equipment} error {error_code}?',
                'context': 'The {equipment} shows error {error_code} when {problem}. To fix: {solution}',
                'answer': '{solution}'
            },
            {
                'question': 'What causes {equipment} to {problem}?',
                'context': '{equipment} may {problem} due to {cause}. Check {check_point}.',
                'answer': '{cause}'
            },
            {
                'question': 'How to maintain {equipment}?',
                'context': 'Regular maintenance of {equipment} includes {maintenance_steps}.',
                'answer': '{maintenance_steps}'
            }
        ]
        
        # Entity values
        values = {
            'equipment': ['AC', 'refrigerator', 'washing machine', 'motor', 'pump'],
            'error_code': ['E01', 'E02', 'F1', 'F2'],
            'problem': ['not cooling', 'making noise', 'not starting', 'leaking'],
            'solution': ['check power supply', 'clean filter', 'replace fuse', 'call technician'],
            'cause': ['low voltage', 'dirty filter', 'worn parts', 'overheating'],
            'check_point': ['power cord', 'circuit breaker', 'fuse box', 'connections'],
            'maintenance_steps': ['clean regularly', 'check connections', 'lubricate parts', 'inspect for damage']
        }
        
        for _ in range(num_pairs):
            template = templates[np.random.randint(len(templates))]
            
            # Fill template
            filled = {}
            for key in template.keys():
                text = template[key]
                for entity, entity_values in values.items():
                    if f'{{{entity}}}' in text:
                        text = text.replace(f'{{{entity}}}', np.random.choice(entity_values))
                filled[key] = text
            
            qa_pairs.append({
                'question': filled['question'],
                'context': filled['context'],
                'answer': filled['answer'],
                'category': 'troubleshooting'
            })
        
        return qa_pairs
    
    def save_dataset(self, qa_pairs: List[Dict], split: str = 'train'):
        """Save knowledge dataset"""
        output_file = self.output_dir / f'knowledge_{split}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(qa_pairs, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(qa_pairs)} QA pairs to {output_file}")
    
    def prepare_datasets(self, num_pairs: int = 5000):
        """Prepare knowledge retrieval datasets"""
        logger.info("Creating synthetic QA pairs...")
        qa_pairs = self.create_synthetic_qa_pairs(num_pairs)
        
        # Split into train/val/test (80/10/10)
        train_pairs, temp_pairs = train_test_split(qa_pairs, test_size=0.2, random_state=42)
        val_pairs, test_pairs = train_test_split(temp_pairs, test_size=0.5, random_state=42)
        
        self.save_dataset(train_pairs, 'train')
        self.save_dataset(val_pairs, 'val')
        self.save_dataset(test_pairs, 'test')
        
        logger.info(f"Dataset split: Train={len(train_pairs)}, Val={len(val_pairs)}, Test={len(test_pairs)}")


class SchemeDatasetPreparator:
    """Prepare government scheme matching datasets"""
    
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def create_synthetic_schemes(self, num_schemes: int = 100) -> List[Dict]:
        """Create synthetic government scheme data"""
        schemes = []
        
        scheme_templates = [
            {
                'name': 'Pradhan Mantri {trade} Yojana',
                'description': 'Financial assistance for {trade} workers',
                'eligibility': {
                    'age_min': 18,
                    'age_max': 60,
                    'income_max': 300000,
                    'trade': '{trade}'
                },
                'benefits': 'Subsidy of {amount} rupees',
                'documents': ['Aadhaar', 'Income Certificate', 'Trade Certificate']
            },
            {
                'name': '{state} {trade} Skill Development Scheme',
                'description': 'Training and certification for {trade}',
                'eligibility': {
                    'age_min': 18,
                    'age_max': 45,
                    'state': '{state}',
                    'trade': '{trade}'
                },
                'benefits': 'Free training and {amount} stipend',
                'documents': ['Aadhaar', 'Residence Proof', 'Education Certificate']
            }
        ]
        
        trades = ['Plumber', 'Electrician', 'Carpenter', 'Mason', 'Welder']
        states = ['Madhya Pradesh', 'Rajasthan', 'Jammu Kashmir', 'Kerala', 'Punjab']
        amounts = ['10000', '25000', '50000', '100000']
        
        for i in range(num_schemes):
            template = scheme_templates[i % len(scheme_templates)]
            trade = trades[i % len(trades)]
            state = states[i % len(states)]
            amount = amounts[i % len(amounts)]
            
            scheme = {
                'scheme_id': f'SCHEME_{i:04d}',
                'name': template['name'].replace('{trade}', trade).replace('{state}', state),
                'description': template['description'].replace('{trade}', trade),
                'eligibility': template['eligibility'].copy(),
                'benefits': template['benefits'].replace('{amount}', amount),
                'documents': template['documents'].copy()
            }
            
            # Replace placeholders in eligibility
            if 'trade' in scheme['eligibility']:
                scheme['eligibility']['trade'] = trade
            if 'state' in scheme['eligibility']:
                scheme['eligibility']['state'] = state
            
            schemes.append(scheme)
        
        return schemes
    
    def create_user_profiles(self, num_profiles: int = 1000) -> List[Dict]:
        """Create synthetic user profiles for matching"""
        profiles = []
        
        trades = ['Plumber', 'Electrician', 'Carpenter', 'Mason', 'Welder']
        states = ['Madhya Pradesh', 'Rajasthan', 'Jammu Kashmir', 'Kerala', 'Punjab']
        
        for i in range(num_profiles):
            profile = {
                'user_id': f'USER_{i:04d}',
                'age': np.random.randint(18, 65),
                'income': np.random.randint(50000, 500000),
                'trade': trades[i % len(trades)],
                'state': states[i % len(states)],
                'education': np.random.choice(['10th', '12th', 'Graduate', 'None']),
                'has_aadhaar': True,
                'has_income_cert': np.random.choice([True, False]),
                'has_trade_cert': np.random.choice([True, False])
            }
            profiles.append(profile)
        
        return profiles
    
    def save_schemes(self, schemes: List[Dict]):
        """Save scheme data"""
        output_file = self.output_dir / 'schemes.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(schemes, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(schemes)} schemes to {output_file}")
    
    def save_profiles(self, profiles: List[Dict], split: str = 'train'):
        """Save user profiles"""
        output_file = self.output_dir / f'profiles_{split}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(profiles, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(profiles)} profiles to {output_file}")
    
    def prepare_datasets(self, num_schemes: int = 500, num_profiles: int = 5000):
        """Prepare scheme matching datasets"""
        logger.info("Creating synthetic scheme data...")
        schemes = self.create_synthetic_schemes(num_schemes)
        self.save_schemes(schemes)
        
        logger.info("Creating synthetic user profiles...")
        profiles = self.create_user_profiles(num_profiles)
        
        # Split profiles into train/val/test (80/10/10)
        train_profiles, temp_profiles = train_test_split(profiles, test_size=0.2, random_state=42)
        val_profiles, test_profiles = train_test_split(temp_profiles, test_size=0.5, random_state=42)
        
        self.save_profiles(train_profiles, 'train')
        self.save_profiles(val_profiles, 'val')
        self.save_profiles(test_profiles, 'test')
        
        logger.info(f"Dataset split: Train={len(train_profiles)}, Val={len(val_profiles)}, Test={len(test_profiles)}")


def main():
    parser = argparse.ArgumentParser(description='Prepare NLP datasets for KarigAI')
    parser.add_argument('--task', type=str, required=True,
                       choices=['intent', 'translation', 'knowledge', 'schemes', 'all'],
                       help='Dataset preparation task')
    parser.add_argument('--output_dir', type=str, default='data/processed/nlp',
                       help='Output directory for processed datasets')
    parser.add_argument('--num_examples', type=int, default=10000,
                       help='Number of examples to generate')
    
    args = parser.parse_args()
    
    if args.task == 'intent' or args.task == 'all':
        logger.info("Preparing intent recognition datasets...")
        preparator = IntentDatasetPreparator(os.path.join(args.output_dir, 'intent'))
        preparator.prepare_datasets(args.num_examples)
    
    if args.task == 'translation' or args.task == 'all':
        logger.info("Preparing translation datasets...")
        preparator = TranslationDatasetPreparator(os.path.join(args.output_dir, 'translation'))
        preparator.prepare_datasets(args.num_examples)
    
    if args.task == 'knowledge' or args.task == 'all':
        logger.info("Preparing knowledge retrieval datasets...")
        preparator = KnowledgeDatasetPreparator(os.path.join(args.output_dir, 'knowledge'))
        preparator.prepare_datasets(args.num_examples // 2)
    
    if args.task == 'schemes' or args.task == 'all':
        logger.info("Preparing government scheme datasets...")
        preparator = SchemeDatasetPreparator(os.path.join(args.output_dir, 'schemes'))
        preparator.prepare_datasets(num_schemes=500, num_profiles=args.num_examples)
    
    logger.info("Dataset preparation complete!")


if __name__ == '__main__':
    main()
