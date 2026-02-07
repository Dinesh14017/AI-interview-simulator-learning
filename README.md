# AI Interview Simulator 🚀

A local-first, AI-powered mock interview application that simulates realistic technical interviews. Built with FastAPI and Ollama, featuring a polished modern UI.

## Features

- **Real-time AI Interviewer**: Powered by local LLMs (Llama 3 via Ollama).
- **Session Management**: Tracks interview stage (Intro → Technical → Scenario → etc.).
- **Adaptive Difficulty**: adjusts questions based on your response length and complexity.
- **Live Scoring & Feedback**: Detailed performance report with strengths and improvement areas at the end.
- **Modern UI**: Dark mode, glassmorphism, and smooth animations.

## Prerequisites

1. **Python 3.8+**
2. **[Ollama](https://ollama.com/)** installed and running.
   - Pull the model: `ollama pull llama3.1` (or your preferred model).

## Quick Start

### 1. Backend Setup
```bash
cd backend
pip install -r requirements.txt
python main.py
```
The server will start at `http://localhost:8000`.

### 2. Frontend Setup
Simply open `frontend/index.html` in your web browser. No build step required!

## Demo Flow

1.  **Start**: Open the app, select "Software Engineer" and "Medium" difficulty.
2.  **Intro**: The AI will ask about your background.
3.  **Technical**: Answer 2-3 technical questions. Keep them short to trigger "elaboration" prompts, or detailed to trigger "depth" prompts.
4.  **End**: Type "I have no more questions" or complete the stages.
5.  **Feedback**: View your score and personalized feedback report.

## Tech Stack
- **Backend**: FastAPI, Uvicorn, HTTPX
- **AI**: Ollama (Local API)
- **Frontend**: Vanilla HTML/CSS/JS (Zero dependencies)
