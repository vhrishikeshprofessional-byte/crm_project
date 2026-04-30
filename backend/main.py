from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json
import os
from agent import run_agent
from database import save_to_mysql, get_db_connection, init_db

app = FastAPI(title="HCP CRM AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

JSON_FILE = "interaction_state.json"


def read_json():
    if not os.path.exists(JSON_FILE):
        return {}
    with open(JSON_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return {}


def write_json(data: dict):
    with open(JSON_FILE, "w") as f:
        json.dump(data, f, indent=2)


def clear_json():
    write_json({})


# ─── Request Models ───────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    interaction_data: dict


# ─── Startup ──────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    init_db()
    print("✅ Database initialized.")


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"message": "HCP CRM AI Backend is running. Visit /docs for API reference."}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Main AI chat endpoint.
    Accepts user message → runs LangGraph agent → returns reply + updated form data.
    Handles all 9 tools: log, edit, get, validate, suggest,
    show_logs, reminders, sentiment, briefing.
    """
    current_data = read_json()

    try:
        result = run_agent(req.message, current_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    # Only write back to JSON if the result contains form-level data
    # (not for show_logs / reminders / sentiment / briefing which return DB data)
    interaction_data = result.get("interaction_data", {})
    form_keys = {"hcp_name", "interaction_type", "date", "time", "attendees",
                 "topics_discussed", "materials_shared", "samples_distributed",
                 "sentiment", "outcomes", "follow_ups"}
    is_form_data = bool(set(interaction_data.keys()) & form_keys)

    if is_form_data:
        write_json(interaction_data)

    return ChatResponse(
        reply=result["reply"],
        interaction_data=interaction_data
    )


@app.get("/interaction")
async def get_interaction():
    """Returns current in-progress interaction from JSON temp file."""
    return read_json()


@app.get("/logs")
async def get_all_logs():
    """Returns all saved interactions from MySQL database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM interactions ORDER BY created_at DESC")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        clean_rows = []
        for row in rows:
            clean_row = {}
            for k, v in row.items():
                if hasattr(v, 'isoformat'):
                    clean_row[k] = v.isoformat()
                elif isinstance(v, (bytes, bytearray)):
                    clean_row[k] = v.decode()
                else:
                    clean_row[k] = v
            clean_rows.append(clean_row)

        return {"logs": clean_rows, "count": len(clean_rows)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.post("/save-interaction")
async def save_interaction():
    """
    Validates current JSON data → saves to MySQL → clears JSON.
    Called when user clicks the Save button.
    """
    data = read_json()

    if not data:
        raise HTTPException(status_code=400, detail="No interaction data to save. Please log an interaction first.")

    required = ["hcp_name", "interaction_type", "date"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required fields: {', '.join(missing)}. Please fill them before saving."
        )

    try:
        save_to_mysql(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save to database: {str(e)}")

    clear_json()
    return {"message": "✅ Interaction saved successfully to database.", "saved_data": data}


@app.post("/reset")
async def reset():
    """Clears the current in-progress interaction JSON. Resets the form."""
    clear_json()
    return {"message": "🔄 Interaction state cleared."}


@app.delete("/logs/{log_id}")
async def delete_log(log_id: int):
    """Delete a specific interaction log by ID."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM interactions WHERE id = %s", (log_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Log with id {log_id} not found.")
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": f"✅ Log {log_id} deleted successfully."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")