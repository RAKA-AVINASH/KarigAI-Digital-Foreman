# KarigAI: Empowering the Blue-Collar Workforce with AI

![Hackathon Project](https://img.shields.io/badge/Status-MVP_Completed-brightgreen)
![Flutter](https://img.shields.io/badge/Frontend-Flutter-blue)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688)
![AI/ML](https://img.shields.io/badge/AI_Engine-LLM_%7C_Vision-orange)

**KarigAI** is an intelligent, multi-lingual, and highly optimized digital assistant designed specifically for blue-collar workers (Karigars) in the unorganized sector. It bridges the digital divide by offering AI-powered technical assistance, smart financial management, personalized learning, and automated government scheme discovery.

---

##  Key Features (The 4 Pillars)

### 1. AI Mistri (Vision & Repair Assistant)
* **Visual Fault Detection:** Karigars can upload images of broken equipment.
* **Step-by-Step Guidance:** AI analyzes the image and provides exact repair steps in the local language.

### 2. AI Ustad (Learning & Upskilling)
* **Contextual Memory:** A conversational AI tutor that remembers past interactions for a personalized learning experience.
* **Micro-Learning:** Generates instant quizzes and awards XP points to gamify the upskilling process.

### 3. Voice Accountant (Financial Management)
* **Voice-to-Invoice:** Converts simple voice notes into professional, itemized invoices.
* **Smart Contracts:** Generates basic work agreements to ensure payment security.

### 4. Yojana (Government Scheme Matching)
* **Dynamic Eligibility Engine:** Matches the Karigar's profile with real-time government schemes.
* **Form Auto-Filling:** Automatically extracts profile data to pre-fill complex scheme applications with secure tracking IDs.

---

## System Architecture & MLOps



We built KarigAI with an enterprise-grade mindset, focusing on low latency and cost optimization:
* **Unified API Gateway:** Built with FastAPI, featuring request routing and performance benchmarking (`X-Process-Time` headers).
* **Smart Edge Caching (0ms Latency):** In-memory cache short-circuits repetitive queries, completely bypassing expensive Cloud API calls.
* **System Monitoring:** Live health checks (`/health`) and usage analytics (`/admin/metrics`) track cache hits vs. cloud hits.
* **Resilience:** Fallback mechanisms in the Flutter SDK ensure the app gracefully handles network degradations without crashing.

---

## Tech Stack

* **Frontend:** Flutter (Dart) - Cross-platform mobile application.
* **Backend:** Python 3.x, FastAPI, Uvicorn.
* **AI/ML Layer:** Integration with advanced LLMs (Vision & Text) and structured JSON output parsing.
* **Infrastructure:** Localhost/Ngrok (Dev), Google Colab Deployment Automation (Prod Ready).

---





## Getting Started (Local Setup)

### Prerequisites
* Flutter SDK
* Python 3.9+
* Git

### 1. Backend Setup (FastAPI)
```bash
# Navigate to the backend directory (if separated) or project root
cd Karigai_backend/ml_models/models/colab_models

# Create and activate virtual environment (Windows)
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install fastapi uvicorn python-multipart requests

# Run the API Gateway server
uvicorn server:app --reload




# Frontend Setup
# Navigate to the flutter app directory
cd karigai_app

# Get dependencies
flutter pub get

# Run the app
flutter run