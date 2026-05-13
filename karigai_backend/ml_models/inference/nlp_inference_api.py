"""
NLP Inference API for KarigAI

This FastAPI service provides endpoints for all NLP models:
- Intent recognition and entity extraction
- Translation and language transformation
- Knowledge retrieval and QA
- Government scheme matching
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    AutoModel,
    MBartForConditionalGeneration,
    MBart50TokenizerFast
)
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="KarigAI NLP Inference API",
    description="NLP models for intent recognition, translation, knowledge retrieval, and scheme matching",
    version="1.0.0"
)

# Global model storage
models = {}
tokenizers = {}


# Request/Response Models
class IntentRequest(BaseModel):
    text: str
    language: str = "hi"


class IntentResponse(BaseModel):
    intent: str
    confidence: float
    entities: List[Dict]


class TranslationRequest(BaseModel):
    text: str
    source_lang: str
    target_lang: str
    register: str = "formal"  # colloquial, formal, technical


class TranslationResponse(BaseModel):
    translated_text: str
    source_lang: str
    target_lang: str


class KnowledgeRequest(BaseModel):
    question: str
    top_k: int = 5


class KnowledgeResponse(BaseModel):
    answers: List[Dict]
    confidence_scores: List[float]


class SchemeRequest(BaseModel):
    user_profile: Dict
    top_k: int = 5


class SchemeResponse(BaseModel):
    schemes: List[Dict]
    eligibility_scores: List[float]


# Model Loading Functions
def load_intent_model(model_path: str):
    """Load intent recognition model"""
    logger.info(f"Loading intent recognition model from {model_path}")
    
    tokenizer = AutoTokenizer.from_pretrained('distilbert-base-multilingual-cased')
    model = AutoModelForSequenceClassification.from_pretrained(model_path)
    model.eval()
    
    # Load intent labels
    with open(os.path.join(model_path, 'intent_labels.json'), 'r') as f:
        intent_labels = json.load(f)
    
    models['intent'] = model
    tokenizers['intent'] = tokenizer
    models['intent_labels'] = intent_labels
    
    logger.info("Intent recognition model loaded successfully")


def load_translation_model(model_path: str):
    """Load translation model"""
    logger.info(f"Loading translation model from {model_path}")
    
    tokenizer = MBart50TokenizerFast.from_pretrained(model_path)
    model = MBartForConditionalGeneration.from_pretrained(model_path)
    model.eval()
    
    models['translation'] = model
    tokenizers['translation'] = tokenizer
    
    logger.info("Translation model loaded successfully")


def load_knowledge_model(model_path: str):
    """Load knowledge retrieval model"""
    logger.info(f"Loading knowledge retrieval model from {model_path}")
    
    tokenizer = AutoTokenizer.from_pretrained('bert-base-multilingual-cased')
    
    # Load dual encoder
    question_encoder = AutoModel.from_pretrained(os.path.join(model_path, 'question_encoder'))
    context_encoder = AutoModel.from_pretrained(os.path.join(model_path, 'context_encoder'))
    
    question_encoder.eval()
    context_encoder.eval()
    
    models['knowledge_question'] = question_encoder
    models['knowledge_context'] = context_encoder
    tokenizers['knowledge'] = tokenizer
    
    # Load knowledge base
    with open(os.path.join(model_path, 'knowledge_base.json'), 'r', encoding='utf-8') as f:
        knowledge_base = json.load(f)
    
    models['knowledge_base'] = knowledge_base
    
    logger.info("Knowledge retrieval model loaded successfully")


def load_scheme_model(model_path: str):
    """Load scheme matching model"""
    logger.info(f"Loading scheme matching model from {model_path}")
    
    tokenizer = AutoTokenizer.from_pretrained('distilbert-base-multilingual-cased')
    model = AutoModelForSequenceClassification.from_pretrained(model_path)
    model.eval()
    
    models['scheme'] = model
    tokenizers['scheme'] = tokenizer
    
    # Load schemes database
    with open(os.path.join(model_path, 'schemes.json'), 'r', encoding='utf-8') as f:
        schemes = json.load(f)
    
    models['schemes_db'] = schemes
    
    logger.info("Scheme matching model loaded successfully")


# API Endpoints
@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "KarigAI NLP Inference API",
        "version": "1.0.0",
        "endpoints": [
            "/intent",
            "/translate",
            "/knowledge",
            "/schemes",
            "/health"
        ]
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "models_loaded": list(models.keys())
    }


@app.post("/intent", response_model=IntentResponse)
def recognize_intent(request: IntentRequest):
    """Recognize intent and extract entities"""
    try:
        if 'intent' not in models:
            raise HTTPException(status_code=503, detail="Intent model not loaded")
        
        # Tokenize
        tokenizer = tokenizers['intent']
        inputs = tokenizer(
            request.text,
            max_length=128,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        # Predict
        with torch.no_grad():
            outputs = models['intent'](**inputs)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=-1)
            pred_idx = torch.argmax(probs, dim=-1).item()
            confidence = probs[0, pred_idx].item()
        
        # Get intent label
        intent_labels = models['intent_labels']
        intent = intent_labels[pred_idx]
        
        # Extract entities (simplified - would use NER model in production)
        entities = []
        
        return IntentResponse(
            intent=intent,
            confidence=confidence,
            entities=entities
        )
    
    except Exception as e:
        logger.error(f"Error in intent recognition: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/translate", response_model=TranslationResponse)
def translate_text(request: TranslationRequest):
    """Translate text between languages"""
    try:
        if 'translation' not in models:
            raise HTTPException(status_code=503, detail="Translation model not loaded")
        
        # Language code mapping
        lang_map = {
            'hi': 'hi_IN',
            'en': 'en_XX',
            'ml': 'ml_IN',
            'pa': 'pa_IN',
            'bn': 'bn_IN',
            'ta': 'ta_IN',
            'te': 'te_IN'
        }
        
        source_lang = lang_map.get(request.source_lang, 'en_XX')
        target_lang = lang_map.get(request.target_lang, 'en_XX')
        
        # Tokenize
        tokenizer = tokenizers['translation']
        tokenizer.src_lang = source_lang
        inputs = tokenizer(request.text, return_tensors='pt')
        
        # Translate
        with torch.no_grad():
            generated_ids = models['translation'].generate(
                **inputs,
                forced_bos_token_id=tokenizer.lang_code_to_id[target_lang],
                max_length=128,
                num_beams=4
            )
        
        translated_text = tokenizer.decode(generated_ids[0], skip_special_tokens=True)
        
        return TranslationResponse(
            translated_text=translated_text,
            source_lang=request.source_lang,
            target_lang=request.target_lang
        )
    
    except Exception as e:
        logger.error(f"Error in translation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/knowledge", response_model=KnowledgeResponse)
def retrieve_knowledge(request: KnowledgeRequest):
    """Retrieve relevant knowledge for a question"""
    try:
        if 'knowledge_question' not in models:
            raise HTTPException(status_code=503, detail="Knowledge model not loaded")
        
        # Encode question
        tokenizer = tokenizers['knowledge']
        question_inputs = tokenizer(
            request.question,
            max_length=256,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        with torch.no_grad():
            question_outputs = models['knowledge_question'](**question_inputs)
            question_embedding = question_outputs.last_hidden_state[:, 0, :].squeeze()
        
        # Retrieve from knowledge base (simplified - would use vector DB in production)
        knowledge_base = models['knowledge_base']
        answers = []
        scores = []
        
        for item in knowledge_base[:request.top_k]:
            answers.append({
                'answer': item['answer'],
                'context': item['context']
            })
            scores.append(0.85)  # Placeholder score
        
        return KnowledgeResponse(
            answers=answers,
            confidence_scores=scores
        )
    
    except Exception as e:
        logger.error(f"Error in knowledge retrieval: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/schemes", response_model=SchemeResponse)
def match_schemes(request: SchemeRequest):
    """Match user with eligible government schemes"""
    try:
        if 'scheme' not in models:
            raise HTTPException(status_code=503, detail="Scheme model not loaded")
        
        profile = request.user_profile
        profile_text = f"Age: {profile.get('age')}, Income: {profile.get('income')}, Trade: {profile.get('trade')}, State: {profile.get('state')}"
        
        schemes_db = models['schemes_db']
        matched_schemes = []
        scores = []
        
        tokenizer = tokenizers['scheme']
        
        for scheme in schemes_db[:request.top_k]:
            scheme_text = f"{scheme['name']}. {scheme['description']}. Benefits: {scheme['benefits']}"
            combined_text = f"[PROFILE] {profile_text} [SCHEME] {scheme_text}"
            
            # Tokenize
            inputs = tokenizer(
                combined_text,
                max_length=256,
                padding='max_length',
                truncation=True,
                return_tensors='pt'
            )
            
            # Predict eligibility
            with torch.no_grad():
                outputs = models['scheme'](**inputs)
                logits = outputs.logits
                probs = torch.softmax(logits, dim=-1)
                eligibility_score = probs[0, 1].item()  # Probability of eligible class
            
            if eligibility_score > 0.5:
                matched_schemes.append(scheme)
                scores.append(eligibility_score)
        
        return SchemeResponse(
            schemes=matched_schemes,
            eligibility_scores=scores
        )
    
    except Exception as e:
        logger.error(f"Error in scheme matching: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Startup event
@app.on_event("startup")
def startup_event():
    """Load models on startup"""
    logger.info("Starting NLP Inference API...")
    
    models_dir = Path("models/checkpoints")
    
    # Load models if they exist
    if (models_dir / "intent_recognition").exists():
        load_intent_model(str(models_dir / "intent_recognition"))
    
    if (models_dir / "translation").exists():
        load_translation_model(str(models_dir / "translation"))
    
    if (models_dir / "knowledge_retrieval").exists():
        load_knowledge_model(str(models_dir / "knowledge_retrieval"))
    
    if (models_dir / "scheme_matching").exists():
        load_scheme_model(str(models_dir / "scheme_matching"))
    
    logger.info("NLP Inference API started successfully")


# Main entry point
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='NLP Inference API')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host address')
    parser.add_argument('--port', type=int, default=8001, help='Port number')
    parser.add_argument('--models_dir', type=str, default='models/checkpoints',
                       help='Models directory')
    
    args = parser.parse_args()
    
    # Run server
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info"
    )
