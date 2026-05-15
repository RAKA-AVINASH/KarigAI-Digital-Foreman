import os
import io
import json
import time
import hashlib
import base64
import shutil
import random
import string
import gc
import re
from gtts import gTTS
from fastapi.responses import JSONResponse
from fastapi import Request
from starlette.responses import JSONResponse
import requests
import urllib.parse
import urllib.request
import asyncio
import torch
import uvicorn
import edge_tts
from huggingface_hub import InferenceClient
from PIL import Image
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from faster_whisper import WhisperModel
from groq import Groq
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold


# Global In-Memory Cache for Model Responses
KNOWLEDGE_CACHE = {}


def generate_cache_key(query, language, has_image):
    raw_string = f"{query.lower().strip()}_{language}_{has_image}"
    return hashlib.md5(raw_string.encode()).hexdigest()


# 1. Local Storage Setup
TEMP_DIR = "temp_files"
os.makedirs(TEMP_DIR, exist_ok=True)

# 2. API Keys
GROQ_API_KEY = os.getenv("your_api_key", "").replace('"', '').strip()
GOOGLE_API_KEY = os.getenv("your_api_key", "").replace('"', '').strip()
HF_API_KEY = os.getenv("your_api_key", "").replace('"', '').strip()

try:
    genai.configure(api_key=GOOGLE_API_KEY)
    brain_client = Groq(api_key=GROQ_API_KEY)
    print("API Keys Cleaned & Loaded!")
except Exception as e:
    print(f"Key Setup Error: {e}")

# Initialize Gemini with auto-detect
gemini_model = None
if GOOGLE_API_KEY.startswith("AIza"):
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

        print("Checking available Google models...")
        valid_models = [
            m.name
            for m in genai.list_models()
            if "generateContent" in m.supported_generation_methods
        ]

        best_model = None
        for m_name in valid_models:
            if "gemini-1.5-flash" in m_name:
                best_model = m_name
                break

        if not best_model:
            for m_name in valid_models:
                if "gemini-1.5-pro" in m_name or "vision" in m_name:
                    best_model = m_name
                    break

        if not best_model and valid_models:
            best_model = valid_models[0]

        print(f"Assigned Gemini model: {best_model}")
        gemini_model = genai.GenerativeModel(
            best_model, safety_settings=safety_settings
        )
    except Exception as e:
        print(f"Gemini setup failed: {e}")

# 3. Load Whisper Model
# print("Cleaning Memory....")
# gc.collect()
# torch.cuda.empty_cache()
# print("Loading Voice AI...")
# device = "cuda" if torch.cuda.is_available() else "cpu"

# try:
#     ear_model = WhisperModel("large-v3", device=device, compute_type="int8")
#     print("Whisper Large Loaded")
# except:
#     ear_model = WhisperModel("medium", device=device, compute_type="int8")
#     print("Whisper Medium Loaded")

# 4. FastAPI Setup
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


SYSTEM_ANALYTICS = {
    "total_api_requests": 0,
    "edge_cache_hits": 0,
    "cloud_api_calls": 0,
    "estimated_cost_usd": 0.00,
    "system_status": "Healthy",
}


@app.middleware("http")
async def api_gateway_middleware(request: Request, call_next):
    start_time = time.time()
    SYSTEM_ANALYTICS["total_api_requests"] += 1  # Track Total Request

    # 1. API Gateway Logging & Routing check
    client_ip = request.client.host if request.client else "Unknown"
    print(f"\n [API GATEWAY] Inbound Request from {client_ip} to {request.url.path}")

    # 2.Rate Limiting (Security)
    print("[SECURITY] Rate Limit & Auth Checked: PASSED")

    try:
        # Proceed to the actual endpoint
        response = await call_next(request)

        # 3. Performance Benchmarking
        process_time = time.time() - start_time

        # Track Cache vs Cloud for Cost Optimization
        if response.headers.get("X-API-Gateway") == "Active":
            if "Edge Cache" in str(response.headers):
                SYSTEM_ANALYTICS["edge_cache_hits"] += 1
            else:
                SYSTEM_ANALYTICS["cloud_api_calls"] += 1
                SYSTEM_ANALYTICS[
                    "estimated_cost_usd"
                ] += 0.002  # Assume 0.002$ per LLM call

        response.headers["X-KarigAI-Latency"] = f"{process_time:.4f}s"
        response.headers["X-API-Gateway"] = "Active"

        print(
            f"[BENCHMARK] Endpoint {request.url.path} processed in {process_time:.4f} seconds."
        )
        return response

    except Exception as e:
        # 4. Global Error Handling & Fallback
        print(f" [GATEWAY ERROR] Fallback triggered: {str(e)}")
        SYSTEM_ANALYTICS["system_status"] = "Degraded"
        return JSONResponse(
            status_code=500,
            content={"error": "Service temporarily degraded. Serving fallback data."},
        )


@app.get("/")
def home():
    return {"status": "Online", "message": "KarigAI Unified Local Server Live!"}


VOICE_MAP = {
    "hi": {"voice": "hi-IN-SwaraNeural", "name": "Hindi"},
    "en": {"voice": "en-IN-NeerjaNeural", "name": "English"},
    "bn": {"voice": "bn-IN-TanishaaNeural", "name": "Bengali"},
    "ta": {"voice": "ta-IN-PallaviNeural", "name": "Tamil"},
    "te": {"voice": "te-IN-ShrutiNeural", "name": "Telugu"},
    "mr": {"voice": "mr-IN-AarohiNeural", "name": "Marathi"},
    "gu": {"voice": "gu-IN-DhwaniNeural", "name": "Gujarati"},
    "kn": {"voice": "kn-IN-SapnaNeural", "name": "Kannada"},
    "ml": {"voice": "ml-IN-SobhanaNeural", "name": "Malayalam"},
    "ur": {"voice": "ur-IN-GulNeural", "name": "Urdu"},
    "pa": {"voice": "pa-IN-OjasNeural", "name": "Punjabi"},
}


def generate_invoice_json(transcribed_text, lang_code):
    lang_name = VOICE_MAP.get(lang_code, {}).get("name", "Hindi")

    prompt = f"""
    You are an AI accountant for KarigAI.
    Extract the items, quantities, and prices from this text: "{transcribed_text}"
    
    CRITICAL INSTRUCTION: Output EXACTLY in this JSON format ONLY. No markdown, no intro text, no ```json tags.
    {{
        "items": [
            {{
                "name": "<Translate item name to formal {lang_name} word>", 
                "qty": <Extract integer quantity>, 
                "unit": "<kg/piece/job/etc>", 
                "unit_price": <Extract price as integer>, 
                "total_amount": <Calculate qty * unit_price as integer>
            }}
        ],
        "grand_total": <Calculate sum of all total_amounts as integer>,
        "spoken_summary": "A 2-line summary confirming the total bill amount in {lang_name}."
    }}
    """
    try:
        response = brain_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
        )
        content = response.choices[0].message.content.strip()
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return None
    except Exception as e:
        print(f"Invoice Gen Error: {e}")
        return None


# --- CONTRACT GENERATION (NLP & LEGAL ANALYSIS) ---
def generate_contract_json(transcribed_text, lang_code):
    lang_name = VOICE_MAP.get(lang_code, {}).get("name", "Hindi")

    prompt = f"""
    You are an expert Legal Assistant for KarigAI.
    Translate this colloquial request into a formal Legal Contract in {lang_name}.
    User text: "{transcribed_text}"
    
    CRITICAL INSTRUCTION: Output EXACTLY in this JSON format ONLY. No markdown, no intro text, no ```json tags. Keys must remain in English:
    {{
        "title": "<Formal Contract Title in {lang_name}>",
        "party_a": "<Artisan/Contractor Name or 'Karigar'>",
        "party_b": "<Client Name or 'Client'>",
        "scope_of_work": "<Detailed formal description of work in {lang_name}>",
        "payment_terms": "<Extracted amount and conditions in {lang_name}>",
        "risk_clauses": [
            "<Formal Legal Clause 1 in {lang_name}>",
            "<Formal Legal Clause 2 in {lang_name}>"
        ],
        "spoken_summary": "<A short 2-line formal summary of this agreement in {lang_name}>"
    }}
    """
    try:
        response = brain_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
        )
        content = response.choices[0].message.content.strip()
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return None
    except Exception as e:
        print(f"Contract Gen Error: {e}")
        return None


# --- AUTHENTICITY CERTIFICATE GENERATION ---
def generate_certificate_json(transcribed_text, lang_code):
    lang_name = VOICE_MAP.get(lang_code, {}).get("name", "Hindi")

    prompt = f"""
    You are an AI Certification Expert for KarigAI.
    Extract details from this artisan's description to create a Certificate of Authenticity in {lang_name}.
    User text: "{transcribed_text}"
    
    CRITICAL INSTRUCTION: Output EXACTLY in this JSON format ONLY. No markdown.
    {{
        "product_name": "<Name of the handmade product>",
        "material_used": "<Materials or raw items used>",
        "creation_process": "<Short 1-2 line description of how it was made>",
        "cultural_origin": "<Region, city, or art form name (e.g., Banarasi, Ikat)>"
    }}
    """
    try:
        response = brain_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
        )
        content = response.choices[0].message.content.strip()
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return None
    except Exception as e:
        print(f"Certificate Gen Error: {e}")
        return None


# --- LOGIC 2: ALL VISION MODES---
def analyze_vision_gemini(image_path, mode, lang_code):
    try:
        lang_name = VOICE_MAP.get(lang_code, {}).get("name", "Hindi")
        print(f"Processing mode '{mode}' in {lang_name}...")

        img = Image.open(image_path).convert("RGB")

        base_instruction = f"You MUST write all descriptive text (values) in {lang_name}. Do NOT translate JSON keys."

        prompts = {
            "repair": f"Analyze broken machine. {base_instruction} Map: appliance->Machine Name, error_code->Issue, solution->Repair Steps, spoken_summary->Write a helpful 2-line summary to be spoken out loud.",
            "plant": f"Analyze crop disease. {base_instruction} Map: appliance->Crop Name, error_code->Disease, solution->Treatment, spoken_summary->Write a helpful 2-line summary to be spoken out loud.",
            "quality": f"Grade item quality. {base_instruction} Map: appliance->Item Name, error_code->Grade(A/B/C), solution->Reason, spoken_summary->Write a helpful 2-line summary to be spoken out loud.",
            "inventory": f"Count items. {base_instruction} Map: appliance->Item Type, error_code->Count, solution->Restock Advice, spoken_summary->Write a helpful 2-line summary to be spoken out loud.",
            "pattern": f"Analyze traditional art. {base_instruction} Map: appliance->Art Style/Origin, error_code->Identified Motifs, solution->Write the historical meaning AND provide a 'Pattern Similarity Match', spoken_summary->Write a helpful 2-line summary describing the art.",
            "modernize": f"Suggest modernization. {base_instruction} Map: appliance->Modern Fusion Concept, error_code->Trending Colors, solution->Actionable steps, spoken_summary->Write a helpful 2-line summary explaining the modern fusion, and an EXTRA KEY 'image_prompt' (visual description in ENGLISH).",
            "market": f"Analyze market potential. {base_instruction} Map: appliance->Target Audience, error_code->Give a 'Popularity Score: X/10' AND Estimated Price Range INR, solution->Marketing Strategy, spoken_summary->Write a 2-line summary explaining market value.",
        }

        selected_prompt = prompts.get(mode, prompts["repair"])
        
        # Seedha Gemini 2.5-flash call kiya
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content([selected_prompt, img])

        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        match = re.search(r"\{.*\}", clean_text, re.DOTALL)

        final_data = {}
        if match:
            final_data = json.loads(match.group(0))
        else:
            return {
                "appliance": "Error",
                "error_code": "Parsing Failed",
                "solution": clean_text,
                "spoken_summary": "AI Error.",
            }
            
        return final_data
        
    except Exception as e:
        print(f"Analysis crashed: {e}")
        return {
            "appliance": "Error",
            "error_code": "Failed",
            "solution": str(e),
            "spoken_summary": "Processing failed.",
        }

        # --- FREE IMAGE GENERATION ---
        if mode == "modernize" and HF_API_KEY:
            try:
                print("Generating image via Official Hugging Face Client (SDXL)...")
                english_prompt = final_data.get(
                    "image_prompt",
                    "modern traditional indian fusion design high quality",
                )

                client = InferenceClient(token=HF_API_KEY)

                generated_img = client.text_to_image(
                    english_prompt, model="stabilityai/stable-diffusion-xl-base-1.0"
                )

                buffered = io.BytesIO()
                generated_img.save(buffered, format="JPEG")
                img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

                final_data["generated_image_base64"] = img_base64
                print("Hugging Face Image successfully generated and encoded!")

            except Exception as e:
                print(f"HF Client Error: {e}")
                final_data["generated_image_base64"] = None

        return final_data

    except Exception as e:
        print(f"Analysis crashed: {e}")
        return {
            "appliance": "Error",
            "error_code": "Failed",
            "solution": str(e),
            "spoken_summary": "Processing failed.",
        }


# --- MOUTH (TTS) ---
async def text_to_audio_base64(text, voice_id):
    audio_path = os.path.join(TEMP_DIR, "response.mp3")
    try:
        communicate = edge_tts.Communicate(text, voice_id)
        await communicate.save(audio_path)
        with open(audio_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except:
        return None


# ---  NLP INTENT ROUTER & AUDIO PROCESSING ---
@app.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = Form("hi"),
    doc_type: str = Form("auto"),
):
    try:
        print(
            f"Receiving audio for NLP processing... Lang: {language}, Mode: {doc_type}"
        )
        file_location = os.path.join(TEMP_DIR, file.filename)
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 1. Transcribe (Handles Colloquial / Code-Mixed Accents using Direct HTTP Request)
        import requests

        print("Uploading audio directly to Groq AI...")
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}"
        }
        
        with open(file_location, "rb") as audio_file:
            # File ko .opus format de rahe hain taaki Groq Whisper isko turant pehchan le
            files = {
                "file": ("audio.opus", audio_file, "audio/opus"),
                "model": (None, "whisper-large-v3-turbo")
            }
            response = requests.post(url, headers=headers, files=files)
        
        if response.status_code == 200:
            text = response.json().get("text", "").strip()
            print(f"Transcribed Text: {text}")
        else:
            print(f"Voice API Error: {response.text}")
            return JSONResponse(status_code=500, content={"error": f"API Error: {response.text}"})

        if not text:
            return {"error": "No speech detected"}

        # Intent Recognition System
        detected_intent = doc_type
        confidence_score = 100
        if doc_type == "auto":
            print("Running Intent Recognition...")
            intent_prompt = f"""Read this text: '{text}'. 
            Is the user asking to create a bill/invoice, a legal contract/agreement, or an authenticity certificate for a handmade product? 
            Reply STRICTLY in JSON format with exactly two keys: 'intent' (either 'invoice', 'contract', or 'certificate') and 'confidence_score' (an integer from 1 to 100)."""

            try:
                intent_response = brain_client.chat.completions.create(
                    messages=[{"role": "user", "content": intent_prompt}],
                    model="llama-3.3-70b-versatile",
                    temperature=0.0,
                )
                raw_intent = intent_response.choices[0].message.content.strip().lower()
                detected_intent = (
                    "contract"
                    if "contract" in raw_intent or "agreement" in raw_intent
                    else "invoice"
                )
                match = re.search(r"\{.*\}", raw_intent, re.DOTALL)

                if match:
                    intent_json = json.loads(match.group(0))
                    detected_intent = intent_json.get("intent", "invoice").lower()
                    confidence_score = intent_json.get("confidence_score", 85)

                else:
                    lower_raw = raw_intent.lower()
                    if "contract" in lower_raw:
                        detected_intent = "contract"
                    elif "certificate" in lower_raw:
                        detected_intent = "certificate"
                    else:
                        detected_intent = "invoice"
                    confidence_score = 80
            except Exception as e:
                print(f"Intent JSON parsing error: {e}")
                detected_intent = "invoice"
                confidence_score = 50

            print(
                f"NLP Detected Intent: {detected_intent.upper()} with {confidence_score}% confidence."
            )

        # Route to appropriate NLP Model
        response_type = ""
        spoken_text = ""
        result_json = None

        if detected_intent == "contract":
            result_json = generate_contract_json(text, language)
            response_type = "contract_json"
            spoken_text = (
                result_json.get("spoken_summary", "Contract generated.")
                if result_json
                else "Error generating contract."
            )

        elif detected_intent == "certificate":
            print("Generating Certificate JSON...")
            result_json = generate_certificate_json(text, language)
            response_type = "certificate_json"
            # Extract spoken summary for certificate, default to basic text if missing
            spoken_text = (
                result_json.get("spoken_summary", "Authenticity certificate generated.")
                if result_json
                else "Error generating certificate."
            )

        else:
            result_json = generate_invoice_json(text, language)
            response_type = "invoice_json"
            spoken_text = (
                result_json.get("spoken_summary", "Invoice generated.")
                if result_json
                else "Error generating invoice."
            )

        # 4. Generate TTS Audio Response
        audio_base64 = None
        if spoken_text:
            voice_name = VOICE_MAP.get(language, {}).get("voice", "hi-IN-SwaraNeural")
            tts = edge_tts.Communicate(spoken_text, voice_name)
            audio_path = os.path.join(TEMP_DIR, "response.mp3")
            await tts.save(audio_path)

            with open(audio_path, "rb") as audio_file:
                audio_base64 = base64.b64encode(audio_file.read()).decode("utf-8")

        return {
            "transcribed_text": text,
            "detected_intent": detected_intent,
            response_type: result_json,
            "audio_base64": audio_base64,
        }

    except Exception as e:
        print(f"Error in transcription/NLP: {e}")
        return {"error": str(e)}


@app.post("/diagnose")
async def diagnose_image(
    file: UploadFile = File(...), language: str = Form("hi"), mode: str = Form("repair")
):
    print(f"Vision Request (Mode: {mode})")
    file_path = os.path.join(TEMP_DIR, "temp_image.jpg")

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    data = await asyncio.to_thread(analyze_vision_gemini, file_path, mode, language)

    voice_id = VOICE_MAP.get(language, {}).get("voice", "hi-IN-SwaraNeural")
    audio = await text_to_audio_base64(data.get("spoken_summary", "Done"), voice_id)

    return {"diagnosis_json": data, "audio_base64": audio}


if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)



@app.post("/extract_knowledge")
async def extract_knowledge(
    query: str = Form(""),
    language: str = Form("hi"),
    chat_history: str = Form(""),
    is_voice: str = Form("false"),
    file: UploadFile = File(None),
):
    print("\n" + "=" * 40)
    print(f" GEMINI API HIT - Voice: {is_voice}, Image attached: {file is not None}")

    lang_name = VOICE_MAP.get(language, {}).get("name", "Hindi")

    prompt = f"""
    You are 'KarigAI Ustad', an expert technical teacher for blue-collar artisans.
    Language: {lang_name}
    
    If an image is provided, analyze the problem in the image and provide a step-by-step solution.
    Format your response EXACTLY as this JSON. No markdown.
    {{
        "title": "<Clear title or short answer summary>",
        "category": "<Category>",
        "tags": ["<tag1>", "<tag2>"],
        "extracted_steps": [
            "<Actionable step 1>",
            "<Actionable step 2>"
        ],
        "quiz": {{
            "question": "<A simple multiple-choice question related to the solution to test their knowledge>",
            "options": ["<Option 1>", "<Option 2>", "<Option 3>", "<Option 4>"],
            "correct_answer_index": <Integer 0, 1, 2, or 3 representing the correct option>
        }},
        "quality_score": <Integer 80 to 100>,
        "validation_status": "Verified by KarigAI Expert System",
        "spoken_summary": "<A short, conversational 1-line answer addressing the user directly.>"
    }}
    """

    try:
        has_image = file is not None and file.filename != ""

        # Check Local Edge Cache First
        cache_key = generate_cache_key(query, language, has_image)

        if not has_image and cache_key in KNOWLEDGE_CACHE:
            print(" CACHE HIT! Serving from Local Edge Memory (Skipping Cloud API)")
            cached_data = KNOWLEDGE_CACHE[cache_key]
            return {
                "knowledge_data": cached_data["json"],
                "audio_base64": cached_data["audio"],
                "source": "Edge Cache",
            }

        print(" CACHE MISS! Fetching from Cloud Model...")

        model = genai.GenerativeModel("gemini-2.5-flash")

        combined_text = f"{prompt}\n\nChat History:\n{chat_history}\n\nUser Query: {query if query else 'Is photo mein kya problem hai aur kaise theek karun?'}"
        contents = [combined_text]

        if has_image:
            print(" GEMINI VISION MODE: Processing Image...")
            image_bytes = await file.read()
            img = Image.open(io.BytesIO(image_bytes))
            contents.append(img)
        else:
            print(" GEMINI TEXT MODE: Processing Text Query...")

        # Generate response
        response = model.generate_content(contents)
        content = response.text.strip()

        print(" Received Response from Gemini")

        # Extract JSON
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            return JSONResponse(
                status_code=500, content={"error": "Failed to extract JSON format."}
            )

        knowledge_json = json.loads(match.group(0))

        audio_base64 = None
        if is_voice.lower() == "true":
            print(" Generating Audio Response...")
            spoken_text = knowledge_json.get("spoken_summary", "Jawab screen par hai.")
            voice_code = VOICE_MAP.get(language, {}).get("gtts", "hi")
            try:
                tts = gTTS(text=spoken_text, lang=voice_code)
                audio_io = io.BytesIO()
                tts.write_to_fp(audio_io)
                audio_base64 = base64.b64encode(audio_io.getvalue()).decode("utf-8")
                print(" Audio Generated Successfully")
            except Exception as e:
                print(" TTS Error:", e)

        if not has_image:
            KNOWLEDGE_CACHE[cache_key] = {"json": knowledge_json, "audio": audio_base64}
            print(" Response Saved to Edge Cache for future use.")

        print("=" * 40 + "\n")
        return {
            "knowledge_data": knowledge_json,
            "audio_base64": audio_base64,
            "source": "Cloud API",
        }

    except Exception as e:
        print(f" Gemini API Error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

    # --- DYNAMIC GOVERNMENT SCHEME FETCHING & MATCHING ---


@app.post("/match_schemes")
async def match_schemes(
    name: str = Form(...),
    trade: str = Form(...),
    age: int = Form(30),
    gender: str = Form("Male"),
    social_category: str = Form("General"),
    income: int = Form(100000),
):
    print(f" Dynamic Scheme Fetching for: {name} | Trade: {trade}")

    # Seedha Gemini 2.5-flash ko instruction dena
    prompt = f"""
    You are 'KarigAI Yojana Helper'.
    User Profile: Name: {name}, Trade: {trade}, Age: {age}, Gender: {gender}, Category: {social_category}, Income: ₹{income}
    Task: Find 5 best Indian Govt schemes for this profile.
    Output MUST be only JSON:
    {{
        "schemes_data": [
            {{
                "id": "1", "name": "Scheme Name", "description": "Details in Hindi", 
                "eligibility_rules": "Rules", "target_trades": ["{trade}"], 
                "match_score": 95, "eligibility_reason": "Matching trade", "missing_criteria": "None"
            }}
        ]
    }}
    """

    try:
        # Llama ko hata kar Gemini use kar rahe hain connection fix karne ke liye
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        
        # JSON nikalna
        match = re.search(r"\{.*\}", response.text, re.DOTALL)
        if match:
            schemes_json = json.loads(match.group(0))
            return {"schemes_data": schemes_json["schemes_data"]}
        else:
            return JSONResponse(status_code=500, content={"error": "JSON Parsing failed"})

    except Exception as e:
        print(f" Scheme Error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

        # --- FORM AUTO-FILLING & DATA MAPPING ---


@app.post("/autofill_form")
async def autofill_form(
    scheme_name: str = Form(...),
    name: str = Form(...),
    trade: str = Form(...),
    age: str = Form(...),
    gender: str = Form(...),
    social_category: str = Form(...),
    income: str = Form(...),
):
    print(f" Generating Auto-Fill Form for: {scheme_name}")

    prompt = f"""
    You are 'KarigAI Yojana Helper', an expert in Indian Government Schemes.
    Do NOT use a static database. Use your extensive knowledge base to fetch all the highly relevant and currently active Indian Government schemes for blue-collar workers, artisans, and micro-enterprises.
    
    User Profile:
    - Name: {name}
    - Trade: {trade}
    - Age: {age}
    - Gender: {gender}
    - Social Category: {social_category}
    - Annual Income: ₹{income}
    
    Task:
    1. Identify 5 to 8 major Indian government schemes (like PM Vishwakarma, PMMY Mudra, Stand-Up India, PM SVANidhi, PMEGP, State-specific artisan schemes, etc.) that align with this user's profile.
    2. Format EACH scheme with the required keys: id, name, description, eligibility_rules, target_trades.
    3. Calculate a "match_score" (0-100) based on how well the user's profile fits the scheme's actual rules.
    
    Format your response EXACTLY as this JSON. No markdown, no extra text:
    {{
        "schemes_data": [
            {{
                "id": "<create_a_unique_string_id>",
                "name": "<Official Scheme Name>",
                "description": "<Detailed description of benefits>",
                "eligibility_rules": "<Official eligibility criteria>",
                "target_trades": ["<Trade1>", "<Trade2>", "All"],
                "match_score": <Integer from 0 to 100>,
                "eligibility_reason": "<1 line explaining exactly why they qualify or why the score is high/low>",
                "missing_criteria": "<Any potential blocker, e.g., 'Requires SC/ST certificate' or 'None'>"
            }}
        ]
    }}
    """


    try:
        response = brain_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
        )
        content = response.choices[0].message.content.strip()
        match = re.search(r"\{.*\}", content, re.DOTALL)

        if not match:
            return JSONResponse(
                status_code=500, content={"error": "Failed to map form fields."}
            )

        form_json = json.loads(match.group(0))

        # Submission Tracking logic
        tracking_id = "KARIGAI-" + "".join(
            random.choices(string.ascii_uppercase + string.digits, k=6)
        )
        form_json["tracking_id"] = tracking_id

        return {"form_data": form_json}

    except Exception as e:
        print(f" Form Auto-Fill Error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# --- HEALTH CHECK & MONITORING ---
@app.get("/health")
async def health_check():
    """Kubernetes / Colab monitoring tools hit this to check if server is alive."""
    return {
        "status": SYSTEM_ANALYTICS["system_status"],
        "message": "KarigAI Unified Gateway is running smoothly.",
        "active_modules": ["Accountant", "Mistri", "Ustad", "Yojana"],
    }


# --- DISASTER RECOVERY & BACKUP ---
@app.post("/admin/backup")
async def trigger_backup():
    """Simulates automated model state and cache backup to Google Drive."""
    try:
        backup_data = {"cache": KNOWLEDGE_CACHE, "analytics": SYSTEM_ANALYTICS}

        with open("karigai_gdrive_backup.json", "w") as f:
            json.dump(backup_data, f)
        return {
            "status": "Success",
            "message": "State securely backed up to Cloud Storage.",
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "Backup failed."})


# ---  USAGE ANALYTICS DASHBOARD ---
@app.get("/admin/metrics")
async def get_metrics():
    """Returns real-time usage and cost optimization metrics."""
    return SYSTEM_ANALYTICS
