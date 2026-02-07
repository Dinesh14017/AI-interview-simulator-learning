const API_URL = 'http://localhost:8001';

// State
let state = {
    sessionId: null,
    role: null,
    company: null,
    difficulty: null,
    isWaiting: false,
    isConnected: false
};

// DOM Elements
const els = {
    chatContainer: document.getElementById('chat-container'),
    userInput: document.getElementById('user-input'),
    sendBtn: document.getElementById('send-btn'),
    modal: document.getElementById('start-modal'),
    startBtn: document.getElementById('start-btn'),
    roleSelect: document.getElementById('role-select'),
    companySelect: document.getElementById('company-select'),
    difficultyInputs: document.querySelectorAll('input[name="difficulty"]'),
    statusDot: document.querySelector('.status-dot'),
    statusText: document.querySelector('.status-text'),
    welcome: document.getElementById('welcome-message'),
    typingIndicator: document.getElementById('typing-indicator'),
    restartBtn: document.getElementById('restart-btn'),
    inputWrapper: document.querySelector('.input-wrapper'),
    // Sidebar elements
    vacancyPanel: document.getElementById('vacancy-panel'),
    companyName: document.getElementById('sidebar-company-name'),
    roleName: document.getElementById('sidebar-role'),
    salary: document.getElementById('sidebar-salary'),
    logoPlaceholder: document.querySelector('.company-logo-placeholder')
};

// --- Initialization ---
init();

function init() {
    // 1. Listeners First
    els.startBtn.addEventListener('click', startInterview);
    els.sendBtn.addEventListener('click', handleSend);
    els.userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    });

    els.userInput.addEventListener('input', autoResizeInput);
    els.restartBtn.addEventListener('click', () => window.location.reload());

    // 2. Health & State
    checkHealth();

    // 3. Parse URL Params
    const urlParams = new URLSearchParams(window.location.search);
    const companyParam = urlParams.get('company');
    const roleParam = urlParams.get('role');
    const difficultyParam = urlParams.get('difficulty');
    const autostartParam = urlParams.get('autostart');

    console.log("DEBUG: Init with params:", { companyParam, roleParam, difficultyParam, autostartParam });

    // Apply Context if Company Param exists
    if (companyParam) {
        if (els.companySelect) els.companySelect.value = companyParam;
        applyCompanyContext(companyParam);
    }

    if (roleParam && els.roleSelect) {
        els.roleSelect.value = roleParam;
    }

    if (difficultyParam) {
        els.difficultyInputs.forEach(input => {
            if (input.value === difficultyParam) input.checked = true;
        });
    }

    // 4. Handle Modal vs Auto-start
    if (autostartParam === 'true') {
        console.log("DEBUG: Triggering Auto-start");
        els.modal.classList.remove('active');
        els.welcome.innerHTML = '<h2>Preparing your interview...</h2><p>Our AI is setting up the session. Please wait.</p>';
        startInterview();
    } else {
        els.modal.classList.add('active');
    }
}

// --- Actions ---

async function startInterview() {
    const role = els.roleSelect.value;
    const company = els.companySelect.value;
    const difficulty = Array.from(els.difficultyInputs).find(r => r.checked)?.value || 'medium';

    console.log(`DEBUG: Starting interview for ${role} @ ${company} (${difficulty})`);
    setLoading(els.startBtn, true, 'Starting...');

    // Feedback for autostart
    if (!els.modal.classList.contains('active')) {
        showTyping(true);
        const sysMsg = document.createElement('div');
        sysMsg.className = 'message system-message';
        sysMsg.textContent = "Connecting to AI Interviewer...";
        els.chatContainer.appendChild(sysMsg);
    }

    try {
        const res = await fetch(`${API_URL}/interview/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ role, difficulty, company })
        });

        if (!res.ok) {
            const errorData = await res.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(errorData.detail || 'Start failed');
        }

        const data = await res.json();
        console.log("DEBUG: Session Started:", data.session_id);

        // Success
        state.sessionId = data.session_id;
        state.role = role;
        state.company = company;
        state.difficulty = difficulty;

        // UI Transition
        els.modal.classList.remove('active');
        els.welcome.style.display = 'none';
        els.restartBtn.style.display = 'block';

        showTyping(false);
        // Remove system message if exists
        const sys = document.querySelector('.system-message');
        if (sys) sys.remove();

        enableInput(true);
        addMessage(data.message, 'ai');

    } catch (err) {
        console.error("Start Interview Error:", err);
        showTyping(false);
        alert(`Could not start session. Error: ${err.message}`);
        // If it was an auto-start, show the modal so they can retry manually
        els.modal.classList.add('active');
    } finally {
        setLoading(els.startBtn, false, 'Start Interview');
    }
}

async function handleSend() {
    const text = els.userInput.value.trim();
    if (!text || state.isWaiting) return;

    // UI Updates
    addMessage(text, 'user');
    els.userInput.value = '';
    els.userInput.style.height = 'auto'; // Reset size
    enableInput(false);

    state.isWaiting = true;
    showTyping(true);

    try {
        const res = await fetch(`${API_URL}/interview/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: state.sessionId,
                messages: [{ role: 'user', content: text }],
                role: state.role
            })
        });

        if (!res.ok) throw new Error('Chat failed');

        // Streaming Logic
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let aiText = '';

        // Create bubble immediately
        showTyping(false); // Hide dots
        const bubble = createMessageBubble('ai'); // Create empty bubble
        els.chatContainer.appendChild(bubble);

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));

                        if (data.content) {
                            aiText += data.content;
                            bubble.textContent = aiText;
                            scrollToBottom();
                        }

                        if (data.done) {
                            if (data.stage === 'end') {
                                setTimeout(() => endInterview(), 800);
                            }
                        }
                    } catch (e) { /* ignore partial json */ }
                }
            }
        }

    } catch (err) {
        addMessage('Error connecting to AI.', 'system');
    } finally {
        // Only re-enable if interview not ended
        if (!document.querySelector('.feedback-card')) {
            enableInput(true);
            state.isWaiting = false;
        }
    }
}

async function endInterview() {
    enableInput(false);
    showTyping(true);
    state.isWaiting = true; // Block input

    // UI Feedback that we are finishing
    const finishMsg = document.createElement('div');
    finishMsg.className = 'message system-message';
    finishMsg.textContent = "Interview completed. Analyzing performance...";
    els.chatContainer.appendChild(finishMsg);
    scrollToBottom();

    try {
        const res = await fetch(`${API_URL}/interview/end`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: state.sessionId })
        });

        const data = await res.json();
        showTyping(false);
        renderFeedback(data);

    } catch (err) {
        addMessage("Could not load feedback report.", 'system');
    }
}

function applyCompanyContext(company) {
    els.vacancyPanel.style.display = 'flex';
    els.companyName.textContent = company;
    els.logoPlaceholder.textContent = company[0];

    // Simple mock data for demo
    const data = {
        'Amazon': { role: 'SDE-1', salary: '₹18 - 25 LPA', theme: 'theme-amazon' },
        'TCS': { role: 'System Engineer', salary: '₹3.6 - 7 LPA', theme: 'theme-tcs' },
        'Zoho': { role: 'Software Developer', salary: '₹6 - 12 LPA', theme: 'theme-zoho' }
    };

    const info = data[company] || { role: 'Software Engineer', salary: 'Market Standard', theme: '' };

    els.roleName.textContent = info.role;
    els.salary.textContent = info.salary;

    if (info.theme) {
        document.body.classList.add(info.theme);
    }
}

// --- UI Helpers ---

function addMessage(text, type) {
    const div = createMessageBubble(type);
    div.textContent = text;
    els.chatContainer.appendChild(div);
    scrollToBottom();
}

function createMessageBubble(type) {
    const div = document.createElement('div');
    div.className = `message ${type}-message`;
    return div;
}

function renderFeedback(data) {
    const card = document.createElement('div');
    card.className = 'feedback-card';
    card.innerHTML = `
        <div class="score-badge">${data.score}</div>
        <h2>Analysis Complete</h2>
        <p style="color:var(--text-muted)">${state.role.replace('_', ' ').toUpperCase()} @ ${state.company}</p>
        
        <div class="feedback-section">
            <h3>Strengths</h3>
            <ul class="feedback-list">
                ${data.strengths.map(s => `<li>${s}</li>`).join('')}
            </ul>
        </div>
        
        <div class="feedback-section">
            <h3>Focus Areas</h3>
            <ul class="feedback-list">
                ${data.improvements.map(i => `<li>${i}</li>`).join('')}
            </ul>
        </div>
        
        <button onclick="window.location.reload()" class="primary-btn" style="margin-top:2rem">
            Start New Session
        </button>
    `;
    els.chatContainer.appendChild(card);
    scrollToBottom();
}

function enableInput(enabled) {
    els.userInput.disabled = !enabled;
    els.sendBtn.disabled = !enabled;

    if (enabled) {
        els.inputWrapper.classList.remove('disabled');
        els.userInput.placeholder = "Type your response here...";
        els.userInput.focus();
    } else {
        els.inputWrapper.classList.add('disabled');
        els.userInput.placeholder = state.isWaiting ? "AI is replying..." : "Please wait...";
    }
}

function showTyping(show) {
    if (show) els.typingIndicator.classList.add('visible');
    else els.typingIndicator.classList.remove('visible');
    scrollToBottom();
}

function scrollToBottom() {
    els.chatContainer.scrollTop = els.chatContainer.scrollHeight;
}

function autoResizeInput() {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
    els.sendBtn.disabled = this.value.trim().length === 0;
}

function setLoading(btn, isLoading, text) {
    btn.disabled = isLoading;
    btn.textContent = text;
    if (isLoading) btn.classList.add('disabled');
    else btn.classList.remove('disabled');
}

async function checkHealth() {
    try {
        const res = await fetch(`${API_URL}/health`);
        if (res.ok) {
            els.statusDot.classList.remove('error');
            els.statusDot.classList.add('online');
            els.statusText.textContent = 'Online & Ready';
            state.isConnected = true;
        } else if (res.status === 503) {
            els.statusDot.classList.remove('online');
            els.statusDot.classList.add('error');
            els.statusText.textContent = 'Ollama Offline';
        }
    } catch (e) {
        els.statusDot.classList.remove('online');
        els.statusDot.classList.add('error');
        els.statusText.textContent = 'Backend Offline';
    }
}
