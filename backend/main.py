from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
import json
from typing import Optional, List, Dict
import asyncio
from enum import Enum
from datetime import datetime
import uuid

app = FastAPI(title="AI Interview Simulator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ollama configuration
OLLAMA_URL = "http://localhost:11434"
MODEL_NAME = "llama3.1"  # Change to mistral if you prefer

# Interview stage management
class InterviewStage(str, Enum):
    APTITUDE = "aptitude"  # quantitative/logical
    INTRO = "intro"  # Introductory/behavioral questions
    TECHNICAL = "technical"  # Core technical questions
    SCENARIO = "scenario"  # Scenario-based/problem-solving
    HR = "hr"  # Culture fit, soft skills
    END = "end"  # Wrapping up

# Session state tracking
class SessionState:
    def __init__(self, role: str, difficulty: str, company: str = "Generic"):
        self.session_id = str(uuid.uuid4())
        self.role = role
        self.difficulty = difficulty
        self.company = company
        self.stage = InterviewStage.APTITUDE
        self.questions_asked = 0  # Total questions across all stages
        self.stage_questions = {stage.value: 0 for stage in InterviewStage}  # Questions per stage
        self.created_at = datetime.now()
        self.conversation_history = []  # Store all messages
        self.scores = []  # List of scores (0-10) for each answer
        self.feedback_notes = []  # Raw notes for final summary
        
    def advance_stage(self):
        """Move to next interview stage based on current progress"""
        stage_order = [InterviewStage.APTITUDE, InterviewStage.INTRO, InterviewStage.TECHNICAL, 
                      InterviewStage.SCENARIO, InterviewStage.HR, InterviewStage.END]
        current_idx = stage_order.index(self.stage)
        if current_idx < len(stage_order) - 1:
            self.stage = stage_order[current_idx + 1]
            
    def increment_question(self):
        """Track a new question being asked"""
        self.questions_asked += 1
        self.stage_questions[self.stage.value] += 1
        
    def should_advance_stage(self) -> bool:
        """Determine if we should move to next stage (2 questions per stage)"""
        return self.stage_questions[self.stage.value] >= 2 and self.stage != InterviewStage.END

    def evaluate_response(self, user_content: str) -> str:
        """Simple heuristic to adapt difficulty based on response"""
        # Very basic heuristic: check length and structure
        words = len(user_content.split())
        
        if words < 10:
            return "ADAPTATION: Process the candidate's last answer. It was very short. Ask them to elaborate or provide more specific details."
        elif words > 100:
            return "ADAPTATION: Process the candidate's last answer. It was detailed. You can increase technical depth or move to a related complex topic."
        
        return "ADAPTATION: Maintain current difficulty."

    def score_response(self, response: str):
        """Calculate heuristic score and add notes for an answer"""
        words = len(response.split())
        score = 5.0  # Base score
        
        # Length heuristic
        if words > 20: score += 1
        if words > 50: score += 1
        if words > 100: score += 1
        
        # Structure/Complexity heuristic (simple keyword check)
        keywords = ["because", "implied", "therefore", "however", "example", "structure", "design", "analysis"]
        matches = sum(1 for w in keywords if w in response.lower())
        score += min(matches * 0.5, 2.0)
        
        # Cap score
        score = min(max(score, 1.0), 10.0)
        
        self.scores.append(score)
        self.feedback_notes.append(f"Answer length: {words} words. Score: {score:.1f}. Keywords used: {matches}.")

# In-memory session storage (use Redis/DB for production)
sessions: Dict[str, SessionState] = {}

# Request models
class ChatMessage(BaseModel):
    role: str
    content: str

class InterviewRequest(BaseModel):
    session_id: str  # Required for state tracking
    messages: List[ChatMessage]
    role: str = "software_engineer"  # default role
    difficulty: str = "medium"  # easy, medium, hard

class InterviewStartRequest(BaseModel):
    role: str = "software_engineer"
    difficulty: str = "medium"
    company: str = "Generic"

class InterviewEndRequest(BaseModel):
    session_id: str

# System prompts for different roles
SYSTEM_PROMPTS = {
    "software_engineer": """You are a professional technical interviewer conducting a coding interview.

Guidelines:
- Ask ONE question at a time, wait for the answer
- Start with behavioral questions, then move to technical/coding
- Be encouraging but professional
- Ask follow-up questions based on responses
- Keep responses concise (2-3 sentences max per turn)
- Don't give away answers, guide with hints if needed
- After 5-7 questions, wrap up the interview

Remember: You're evaluating problem-solving, communication, and technical knowledge.""",

    "product_manager": """You are a senior PM interviewer conducting a product sense interview.

Guidelines:
- Ask ONE question at a time about product thinking
- Focus on: strategy, user empathy, metrics, prioritization
- Challenge assumptions politely
- Keep responses brief and conversational
- Ask follow-up based on their answers
- After 5-7 questions, conclude

Remember: Evaluate structured thinking and customer focus.""",

    "data_scientist": """You are a data science interviewer conducting a technical interview.

Guidelines:
- Ask ONE question at a time covering stats, ML, and problem-solving
- Start simple, increase difficulty based on performance
- Ask for explanations, not just answers
- Keep responses concise
- Include both theoretical and practical questions
- After 5-7 questions, wrap up

Remember: Test depth of knowledge and practical application."""
}

# Helper function to build stage-aware system prompts
def get_stage_instruction(stage: InterviewStage, company: str = "Generic") -> str:
    """Return stage-specific instructions for the AI interviewer"""
    
    # Company nuances
    is_service = company in ["TCS", "Infosys", "Wipro", "Accenture", "Capgemini"]
    is_product = company in ["Amazon", "Zoho", "Google", "Microsoft"]
    
    instructions = {
        InterviewStage.APTITUDE: f"Ask a {'simple' if is_service else 'challenging'} quantitative aptitude or logical reasoning question. Options: A, B, C, D. If the user answered the previous question, briefly VALIDATE it first (Correct/Incorrect) then ask the next one. Focus on: {'Basic Math, Series, Analogies' if is_service else 'Probability, Permutation, Data Interpretation'}.",
        InterviewStage.INTRO: "Start with warm introductory/behavioral questions. Ask about background, experience, and motivation. Keep it conversational.",
        InterviewStage.TECHNICAL: f"Now move to core technical questions. {'Focus on basics, SQL, and Java/Python fundamentals.' if is_service else 'Focus on Data Structures, Algorithms, and System Design concepts.'}",
        InterviewStage.SCENARIO: "Present scenario-based or situational questions. Focus on practical application and decision-making.",
        InterviewStage.HR: f"Ask about team fit, work style, and career goals. {'Emphasize willingness to learn and relocate.' if is_service else 'Focus on Leadership Principles and culture fit.'}",
        InterviewStage.END: "Wrap up the interview. Thank the candidate, answer any questions they have, and explain next steps."
    }
    return instructions.get(stage, "")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags", timeout=5.0)
            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "ollama": "connected",
                    "available_models": [m["name"] for m in response.json().get("models", [])]
                }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Ollama not available: {str(e)}")

@app.post("/interview/start")
async def start_interview(request: InterviewStartRequest):
    """Start a new interview session with state tracking"""
    # Create new session
    print(f"DEBUG: Start Interview Request: {request}")
    session = SessionState(role=request.role, difficulty=request.difficulty, company=request.company)
    sessions[session.session_id] = session
    
    # Build system prompt with stage-specific instructions
    base_prompt = SYSTEM_PROMPTS.get(request.role, SYSTEM_PROMPTS["software_engineer"])
    stage_instruction = get_stage_instruction(session.stage, session.company)
    system_prompt = f"{base_prompt}\n\nTARGER COMPANY: {session.company}\nCURRENT STAGE: {session.stage.value.upper()}\n{stage_instruction}"
    
    # Get the first question from the AI
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Hello, I'm ready for the interview."}
    ]
    
    try:
        print(f"DEBUG: Sending to Ollama: {MODEL_NAME}")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": MODEL_NAME,
                    "messages": messages,
                    "stream": False
                },
                timeout=120.0
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_message = result["message"]["content"]
                
                # Store conversation in session
                session.conversation_history.append({"role": "user", "content": "Hello, I'm ready for the interview."})
                session.conversation_history.append({"role": "assistant", "content": ai_message})
                session.increment_question()
                
                return {
                    "session_id": session.session_id,
                    "message": ai_message,
                    "role": request.role,
                    "difficulty": request.difficulty,
                    "stage": session.stage.value,
                    "questions_asked": session.questions_asked
                }
            else:
                print(f"DEBUG: Ollama Error {response.status_code}: {response.text}")
                raise HTTPException(status_code=500, detail=f"Failed to get response from Ollama: {response.text}")
                
    except Exception as e:
        # Cleanup failed session
        print(f"DEBUG: Exception in start_interview: {e}")
        if session.session_id in sessions:
            del sessions[session.session_id]
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/interview/chat")
async def chat_interview(request: InterviewRequest):
    """Continue interview conversation with state management and streaming response"""
    
    # Retrieve session
    session = sessions.get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found. Please start a new interview.")
    
    # Build conversation with stage-aware system prompt
    base_prompt = SYSTEM_PROMPTS.get(request.role, SYSTEM_PROMPTS["software_engineer"])
    stage_instruction = get_stage_instruction(session.stage, session.company)
    
    # Get adaptation guidance based on last user message if exists
    adaptation_instruction = ""
    if request.messages:
        last_user_msg = request.messages[-1].content
        adaptation_instruction = session.evaluate_response(last_user_msg)
        session.score_response(last_user_msg)  # Score the response
        
    system_prompt = f"{base_prompt}\n\nTARGET COMPANY: {session.company}\nCURRENT STAGE: {session.stage.value.upper()}\n{stage_instruction}\n\n{adaptation_instruction}"
    
    # Include conversation history from session + new messages
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(session.conversation_history)
    messages.extend([{"role": msg.role, "content": msg.content} for msg in request.messages])
    
    # Track accumulated AI response for session storage
    accumulated_response = ""
    
    async def generate_response():
        nonlocal accumulated_response
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{OLLAMA_URL}/api/chat",
                    json={
                        "model": MODEL_NAME,
                        "messages": messages,
                        "stream": True
                    },
                    timeout=120.0
                ) as response:
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                if "message" in data and "content" in data["message"]:
                                    content = data["message"]["content"]
                                    accumulated_response += content
                                    yield f"data: {json.dumps({'content': content})}\n\n"
                                    
                                if data.get("done", False):
                                    # Update session state after response completes
                                    # Store user messages
                                    for msg in request.messages:
                                        session.conversation_history.append({"role": msg.role, "content": msg.content})
                                    
                                    # Store AI response
                                    session.conversation_history.append({"role": "assistant", "content": accumulated_response})
                                    session.increment_question()
                                    
                                    # Check if should advance stage
                                    if session.should_advance_stage():
                                        session.advance_stage()
                                    
                                    # Send completion with stage info
                                    yield f"data: {json.dumps({
                                        'done': True,
                                        'stage': session.stage.value,
                                        'questions_asked': session.questions_asked
                                    })}\n\n"
                                    
                            except json.JSONDecodeError:
                                continue
                                
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(generate_response(), media_type="text/event-stream")

@app.post("/interview/end")
async def end_interview(request: InterviewEndRequest):
    """Generate final feedback and score"""
    session = sessions.get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    # Calculate final score
    if not session.scores:
        final_score = 0
    else:
        final_score = sum(session.scores) / len(session.scores)
    
    # Generate feedback using LLM
    feedback_prompt = f"""
    You are a senior technical interviewer. Review these notes from an interview candidate ({session.role}, {session.difficulty} level):
    
    {json.dumps(session.feedback_notes, indent=2)}
    
    The candidate's calculated heuristic score is {final_score:.1f}/10.
    
    Generate a concise JSON feedback report with the following structure:
    {{
        "strengths": ["point 1", "point 2"],
        "improvements": ["point 1", "point 2"],
        "summary": "1-2 sentence summary of performance."
    }}
    Output ONLY valid JSON.
    """
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": MODEL_NAME,
                    "messages": [{"role": "system", "content": feedback_prompt}],
                    "stream": False,
                    "format": "json"  # Force JSON mode if supported by model version
                },
                timeout=45.0
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_content = result["message"]["content"]
                
                # Try to parse JSON from AI response
                try:
                    feedback_data = json.loads(ai_content)
                except json.JSONDecodeError:
                    # Fallback if AI didn't output pure JSON
                    feedback_data = {
                        "strengths": ["Good communication"],
                        "improvements": ["Practice more"],
                        "summary": ai_content[:200]
                    }
                
                return {
                    "score": round(final_score, 1),
                    "strengths": feedback_data.get("strengths", []),
                    "improvements": feedback_data.get("improvements", []),
                    "summary": feedback_data.get("summary", "Interview completed.")
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to generate feedback")
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/")
async def root():
    return {
        "message": "AI Interview Simulator API",
        "endpoints": {
            "health": "/health",
            "start_interview": "/interview/start",
            "chat": "/interview/chat"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
