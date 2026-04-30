# HCP CRM – AI-First Interaction Logger
Full-stack AI CRM for life science field reps. LangGraph + Groq + FastAPI + React + MySQL.

---

# PROJECT STRUCTURE

```text
crm_project/
├── backend/
│   ├── main.py                  ← FastAPI routes
│   ├── agent.py                 ← LangGraph agent + 5 tools
│   ├── database.py              ← MySQL integration
│   ├── requirements.txt         ← Python dependencies
│   └── interaction_state.json   ← Auto-created at runtime
│
└── frontend/
    ├── public/
    │   └── index.html
    ├── src/
    │   ├── index.js             ← React entry point
    │   ├── index.css            ← Global styles (Inter font)
    │   ├── App.js               ← Split-screen layout
    │   ├── App.css
    │   ├── store.js             ← Redux store
    │   ├── api.js               ← Axios API calls
    │   └── components/
    │       ├── Header.js / Header.css
    │       ├── InteractionForm.js / InteractionForm.css
    │       └── ChatPanel.js / ChatPanel.css
    └── package.json
```

---

# ARCHITECTURE DIAGRAM

```text
User (Chat Input)
      │
      ▼
React + Redux (UI State)
  - Left: InteractionForm  ←──────────────────────────────────────┐
  - Right: ChatPanel                                               │
      │                                                            │
      ▼                                                        Redux update
POST /chat                                                         │
      │                                                            │
      ▼                                                            │
FastAPI Backend (main.py)                                          │
      │                                                            │
      ▼                                                            │
LangGraph Agent (agent.py)                                         │
  ┌─────────────────────────────┐                                  │
  │  1. detect_intent (LLM)     │                                  │
  │  2. route to tool:          │                                  │
  │     ├── log_interaction     │                                  │
  │     ├── edit_interaction    │                                  │
  │     ├── get_interaction     │                                  │
  │     ├── validate            │                                  │
  │     └── suggest_followup    │                                  │
  │  3. generate_reply (LLM)    │                                  │
  └─────────────────────────────┘                                  │
      │                                                            │
      ▼                                                            │
interaction_state.json (temp)                                      │
      │                                                            │
      ├──── GET /interaction ─────────────────────────────────────►│
      │
      └──── POST /save-interaction ──► MySQL (interactions table)
```

---

# SETUP – STEP BY STEP

## PREREQUISITES

* Python 3.10+
* Node.js 18+
* MySQL running on localhost (`root / root`)

---

# STEP 1 – Backend Setup

```bash
# Go to backend folder
cd crm_project/backend

# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server
uvicorn main:app --reload --port 8000
```

The server will:

* Auto-create the MySQL database `hcp_crm_db`
* Auto-create the `interactions` table
* Be accessible at: `http://localhost:8000`
* Swagger docs at: `http://localhost:8000/docs`

---

# STEP 2 – Frontend Setup

```bash
# Go to frontend folder
cd crm_project/frontend

# Install dependencies
npm install

# Start React app
npm start
```

App runs at: `http://localhost:3000`

---

# API REFERENCE

# LANGGRAPH AGENT – 5 TOOLS

| Tool                        | Model                     | Purpose                                             |
| --------------------------- | ------------------------- | --------------------------------------------------- |
| `log_interaction_tool`      | `gemma2-9b-it`            | Extract structured CRM fields from natural language |
| `edit_interaction_tool`     | `llama-3.3-70b-versatile` | Patch specific fields based on edit instructions    |
| `get_all_log`               | —                         | Read all the SQL logs                               |
| `validate_interaction_tool` | —                         | Check required fields and return missing fields     |
| `suggest_followup_tool`     | `llama-3.3-70b-versatile` | Generate AI follow-up action suggestions            |

---

# MYSQL TABLE SCHEMA

```sql
CREATE TABLE interactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    hcp_name VARCHAR(255),
    interaction_type VARCHAR(100),
    date DATE,
    time TIME,
    attendees JSON,
    topics_discussed TEXT,
    materials_shared JSON,
    samples_distributed JSON,
    sentiment VARCHAR(50),
    outcomes TEXT,
    follow_ups JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

# CONFIGURATION

| Setting         | Value                   |
| --------------- | ----------------------- |
| Groq API Key    | gsk_d2I2R0HJ...         |
| Primary Model   | gemma2-9b-it            |
| Reasoning Model | llama-3.3-70b-versatile |
| MySQL Host      | localhost               |
| MySQL User      | root                    |
| MySQL Password  | root                    |
| Database        | hcp_crm_db              |
| Temp JSON       | interaction_state.json  |
| Backend Port    | 8000                    |
| Frontend Port   | 3000                    |

---
