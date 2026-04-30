import json
import os
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from database import get_db_connection

GROQ_API_KEY = "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"
JSON_FILE = "interaction_state.json"

primary_llm = ChatGroq(api_key=GROQ_API_KEY, model_name="llama-3.1-8b-instant", temperature=0.1)
reasoning_llm = ChatGroq(api_key=GROQ_API_KEY, model_name="llama-3.3-70b-versatile", temperature=0.2)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _read_json():
    if not os.path.exists(JSON_FILE):
        return {}
    with open(JSON_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return {}

def _write_json(data: dict):
    with open(JSON_FILE, "w") as f:
        json.dump(data, f, indent=2)

def _clean_llm_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()
    try:
        return json.loads(raw)
    except:
        return {}

def _fetch_all_from_db():
    """Fetch all interaction rows from MySQL."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM interactions ORDER BY created_at DESC")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        # Convert non-serializable types
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
        return clean_rows
    except Exception as e:
        return []

# ─── Tool 1: Log Interaction ──────────────────────────────────────────────────

def log_interaction_tool(user_message: str) -> dict:
    existing = _read_json()
    system_prompt = """You are a CRM data extraction AI for life science field reps.
Extract structured HCP interaction data from the user message.
Return ONLY a valid JSON object with these exact fields (use null for missing):
{
  "hcp_name": "string or null",
  "interaction_type": "Meeting or Call or Visit or null",
  "date": "YYYY-MM-DD or null",
  "time": "HH:MM or null",
  "attendees": [],
  "topics_discussed": "string or null",
  "materials_shared": [],
  "samples_distributed": [],
  "sentiment": "Positive or Neutral or Negative or null",
  "outcomes": "string or null",
  "follow_ups": []
}
Output ONLY the JSON. No explanation. No markdown."""
    response = primary_llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_message)])
    extracted = _clean_llm_json(response.content)
    merged = dict(existing)
    for key, value in extracted.items():
        if value is not None and value != [] and value != "":
            merged[key] = value
    _write_json(merged)
    return merged

# ─── Tool 2: Edit Interaction ─────────────────────────────────────────────────

def edit_interaction_tool(user_instruction: str) -> dict:
    existing = _read_json()
    system_prompt = f"""You are a CRM edit assistant. Current interaction data:
{json.dumps(existing, indent=2)}

User wants to change: "{user_instruction}"
Return ONLY a JSON with ONLY the fields that need to change. No explanation."""
    response = reasoning_llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_instruction)])
    patch = _clean_llm_json(response.content)
    valid_fields = ["hcp_name","interaction_type","date","time","attendees","topics_discussed",
                    "materials_shared","samples_distributed","sentiment","outcomes","follow_ups"]
    merged = dict(existing)
    for key, value in patch.items():
        if key in valid_fields:
            merged[key] = value
    _write_json(merged)
    return merged

# ─── Tool 3: Get Interaction ──────────────────────────────────────────────────

def get_interaction_tool() -> dict:
    return _read_json()

# ─── Tool 4: Validate Interaction ────────────────────────────────────────────

def validate_interaction_tool() -> dict:
    data = _read_json()
    required_fields = ["hcp_name", "interaction_type", "date", "topics_discussed"]
    missing = [f for f in required_fields if not data.get(f)]
    warnings = []
    if not data.get("sentiment"):
        warnings.append("sentiment not captured")
    if not data.get("outcomes"):
        warnings.append("no outcomes recorded")
    return {"is_valid": len(missing) == 0, "missing_required": missing, "warnings": warnings, "current_data": data}

# ─── Tool 5: Suggest Follow-up ────────────────────────────────────────────────

def suggest_followup_tool() -> dict:
    data = _read_json()
    system_prompt = """You are a life science CRM assistant. Based on the HCP interaction below,
suggest 3 specific actionable follow-up actions.
Return ONLY: {"suggestions": ["suggestion 1", "suggestion 2", "suggestion 3"]}
No explanation. Output ONLY the JSON."""
    response = reasoning_llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=json.dumps(data))])
    result = _clean_llm_json(response.content)
    suggestions = result.get("suggestions", [])
    existing_followups = data.get("follow_ups", [])
    if not isinstance(existing_followups, list):
        existing_followups = []
    data["follow_ups"] = list(dict.fromkeys(existing_followups + suggestions))
    _write_json(data)
    return {"suggestions": suggestions}

# ─── Tool 6: Show All Logs ────────────────────────────────────────────────────

def get_all_logs_tool() -> dict:
    """Fetch all saved interactions from MySQL and return them."""
    rows = _fetch_all_from_db()
    if not rows:
        return {"logs": [], "count": 0, "message": "No interactions saved yet."}
    return {"logs": rows, "count": len(rows), "message": f"Found {len(rows)} saved interaction(s)."}

# ─── Tool 7: Smart Follow-up Reminder ────────────────────────────────────────

def followup_reminder_tool() -> dict:
    """
    Scans all DB logs for unactioned follow-ups and uses LLM
    to identify which HCPs need urgent attention.
    """
    rows = _fetch_all_from_db()
    if not rows:
        return {"reminders": [], "message": "No logs found to check."}

    # Build a summary of follow-ups per HCP
    hcp_followups = {}
    for row in rows:
        hcp = row.get("hcp_name", "Unknown")
        fups = row.get("follow_ups", [])
        if isinstance(fups, str):
            try:
                fups = json.loads(fups)
            except:
                fups = []
        date = row.get("date") or row.get("created_at", "unknown date")
        if fups:
            if hcp not in hcp_followups:
                hcp_followups[hcp] = []
            hcp_followups[hcp].append({"date": str(date), "follow_ups": fups})

    if not hcp_followups:
        return {"reminders": [], "message": "No pending follow-ups found in any logs."}

    system_prompt = """You are a life science CRM assistant reviewing HCP follow-up data.
Based on the follow-up history below, identify which HCPs need urgent attention.
For each, provide a priority (High/Medium/Low) and a short action note.
Return ONLY this JSON:
{
  "reminders": [
    {"hcp_name": "...", "priority": "High/Medium/Low", "action": "...", "last_date": "..."}
  ]
}
No explanation. Only JSON."""

    response = reasoning_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=json.dumps(hcp_followups))
    ])
    result = _clean_llm_json(response.content)
    reminders = result.get("reminders", [])
    return {"reminders": reminders, "count": len(reminders),
            "message": f"Found {len(reminders)} HCP(s) needing follow-up."}

# ─── Tool 8: HCP Sentiment Trend ─────────────────────────────────────────────

def sentiment_trend_tool(user_message: str) -> dict:
    """
    Pulls all logs for a specific HCP and uses LLM to analyze
    sentiment trend over time. Flags concerning patterns.
    """
    rows = _fetch_all_from_db()
    if not rows:
        return {"trend": [], "warning": None, "message": "No logs found."}

    # Try to extract HCP name from message
    name_prompt = f"""Extract the HCP doctor name from this message: "{user_message}"
Return ONLY: {{"hcp_name": "name or null"}}"""
    name_response = primary_llm.invoke([HumanMessage(content=name_prompt)])
    name_data = _clean_llm_json(name_response.content)
    hcp_name = name_data.get("hcp_name")

    # Filter rows for that HCP (case-insensitive partial match)
    if hcp_name:
        filtered = [r for r in rows if hcp_name.lower() in (r.get("hcp_name") or "").lower()]
    else:
        filtered = rows  # analyze all if no name given

    if not filtered:
        return {"trend": [], "warning": None,
                "message": f"No logs found for {hcp_name or 'this HCP'}."}

    # Build timeline
    timeline = [{"date": str(r.get("date") or r.get("created_at")),
                 "sentiment": r.get("sentiment"), "hcp_name": r.get("hcp_name")} for r in filtered]

    system_prompt = """You are a life science CRM analyst. Analyze the sentiment timeline below.
Identify trends, flag if sentiment is worsening, and give a recommendation.
Return ONLY this JSON:
{
  "trend_summary": "...",
  "warning": "string or null",
  "recommendation": "...",
  "timeline": [{"date": "...", "sentiment": "...", "hcp_name": "..."}]
}
No explanation. Only JSON."""

    response = reasoning_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=json.dumps(timeline))
    ])
    result = _clean_llm_json(response.content)
    result["hcp_name"] = hcp_name
    return result

# ─── Tool 9: Pre-Call Briefing ────────────────────────────────────────────────

def pre_call_briefing_tool(user_message: str) -> dict:
    """
    Before visiting an HCP, pulls all past logs for that doctor
    and generates a smart pre-call briefing using LLM.
    """
    rows = _fetch_all_from_db()
    if not rows:
        return {"briefing": "No past interactions found.", "hcp_name": None}

    # Extract HCP name
    name_prompt = f"""Extract the HCP doctor name from this message: "{user_message}"
Return ONLY: {{"hcp_name": "name or null"}}"""
    name_response = primary_llm.invoke([HumanMessage(content=name_prompt)])
    name_data = _clean_llm_json(name_response.content)
    hcp_name = name_data.get("hcp_name")

    if hcp_name:
        filtered = [r for r in rows if hcp_name.lower() in (r.get("hcp_name") or "").lower()]
    else:
        filtered = rows[:5]  # last 5 if no name

    if not filtered:
        return {"briefing": f"No past interactions found for {hcp_name}.", "hcp_name": hcp_name}

    system_prompt = """You are a pre-call briefing AI for a life science field rep.
Based on the past HCP interaction history below, generate a concise pre-call briefing.
Include: last interaction summary, sentiment history, key topics discussed, pending follow-ups, and suggested talking points.
Return ONLY this JSON:
{
  "hcp_name": "...",
  "last_interaction": "...",
  "sentiment_history": "...",
  "key_topics": ["..."],
  "pending_followups": ["..."],
  "talking_points": ["..."],
  "briefing_summary": "..."
}
No explanation. Only JSON."""

    response = reasoning_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=json.dumps(filtered))
    ])
    result = _clean_llm_json(response.content)
    result["hcp_name"] = hcp_name
    return result


# ─── LangGraph State ──────────────────────────────────────────────────────────

class AgentState(TypedDict):
    user_message: str
    current_data: dict
    intent: str
    tool_result: dict
    reply: str

# ─── Intent Detection ─────────────────────────────────────────────────────────

def detect_intent(state: AgentState) -> AgentState:
    system_prompt = """Classify the user message intent. Reply with ONLY one word:
- log        (describing a new interaction or adding info)
- edit       (changing/updating/correcting existing data)
- get        (asking to see current form data)
- validate   (asking if data is complete or ready to save)
- suggest    (asking for follow-up suggestions for current interaction)
- show_logs  (asking to see saved logs, history, past interactions from database)
- reminders  (asking about overdue follow-ups, who needs attention, pending tasks)
- sentiment  (asking about sentiment trend or pattern for an HCP)
- briefing   (asking for pre-call briefing or summary before visiting an HCP)

Reply with ONLY the single word."""
    response = primary_llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=state["user_message"])])
    intent = response.content.strip().lower().split()[0]
    valid = ["log","edit","get","validate","suggest","show_logs","reminders","sentiment","briefing"]
    if intent not in valid:
        intent = "log"
    return {**state, "intent": intent}

def route_intent(state: AgentState) -> str:
    return state["intent"]

# ─── Executor Nodes ───────────────────────────────────────────────────────────

def execute_log(state: AgentState) -> AgentState:
    return {**state, "tool_result": log_interaction_tool(state["user_message"])}

def execute_edit(state: AgentState) -> AgentState:
    return {**state, "tool_result": edit_interaction_tool(state["user_message"])}

def execute_get(state: AgentState) -> AgentState:
    return {**state, "tool_result": get_interaction_tool()}

def execute_validate(state: AgentState) -> AgentState:
    return {**state, "tool_result": validate_interaction_tool()}

def execute_suggest(state: AgentState) -> AgentState:
    return {**state, "tool_result": suggest_followup_tool()}

def execute_show_logs(state: AgentState) -> AgentState:
    return {**state, "tool_result": get_all_logs_tool()}

def execute_reminders(state: AgentState) -> AgentState:
    return {**state, "tool_result": followup_reminder_tool()}

def execute_sentiment(state: AgentState) -> AgentState:
    return {**state, "tool_result": sentiment_trend_tool(state["user_message"])}

def execute_briefing(state: AgentState) -> AgentState:
    return {**state, "tool_result": pre_call_briefing_tool(state["user_message"])}

# ─── Reply Generator ──────────────────────────────────────────────────────────

def generate_reply(state: AgentState) -> AgentState:
    intent = state["intent"]
    data = state["tool_result"]

    if intent == "log":
        hcp = data.get("hcp_name", "the HCP")
        topics = data.get("topics_discussed", "")
        sentiment = data.get("sentiment", "")
        reply = f"Got it! I've logged the interaction with **{hcp}**."
        if topics:
            reply += f" Topics: {topics}."
        if sentiment:
            reply += f" Sentiment: **{sentiment}**."
        reply += " The form on the left has been updated!"

    elif intent == "edit":
        reply = "Done! I've updated the data based on your instruction. Check the form on the left."

    elif intent == "get":
        hcp = data.get("hcp_name")
        reply = f"Current data for **{hcp}** shown in the form." if hcp else "No data logged yet. Describe your interaction!"

    elif intent == "validate":
        missing = data.get("missing_required", [])
        warnings = data.get("warnings", [])
        if data.get("is_valid"):
            reply = "✅ All required fields filled! You can safely click **Save Interaction**."
            if warnings:
                reply += f" Suggestions: {', '.join(warnings)}."
        else:
            reply = f"⚠️ Missing required fields: **{', '.join(missing)}**. Please provide these before saving."

    elif intent == "suggest":
        suggestions = data.get("suggestions", [])
        reply = "Suggested follow-ups:\n" + "\n".join(f"• {s}" for s in suggestions) if suggestions else "Log more details first."

    elif intent == "show_logs":
        count = data.get("count", 0)
        if count == 0:
            reply = "📋 No interactions saved yet. Log one and hit Save!"
        else:
            logs = data.get("logs", [])
            lines = [f"📋 Found **{count}** saved interaction(s):\n"]
            for i, log in enumerate(logs, 1):
                lines.append(f"{'─'*40}")
                lines.append(f"**{i}. {log.get('hcp_name','Unknown')}**")
                lines.append(f"📅 Date: {log.get('date','?')}  🕐 Time: {log.get('time','?')}")
                lines.append(f"📞 Type: {log.get('interaction_type','?')}")
                lines.append(f"😊 Sentiment: {log.get('sentiment','?')}")
                attendees = log.get('attendees')
                if attendees:
                    if isinstance(attendees, str):
                        import json as _j
                        try: attendees = _j.loads(attendees)
                        except: pass
                    if isinstance(attendees, list) and attendees:
                        lines.append(f"👥 Attendees: {', '.join(attendees)}")
                if log.get('topics_discussed'):
                    lines.append(f"🗂️ Topics: {log.get('topics_discussed')}")
                materials = log.get('materials_shared')
                if materials:
                    if isinstance(materials, str):
                        import json as _j
                        try: materials = _j.loads(materials)
                        except: pass
                    if isinstance(materials, list) and materials:
                        lines.append(f"📄 Materials: {', '.join(materials)}")
                samples = log.get('samples_distributed')
                if samples:
                    if isinstance(samples, str):
                        import json as _j
                        try: samples = _j.loads(samples)
                        except: pass
                    if isinstance(samples, list) and samples:
                        lines.append(f"💊 Samples: {', '.join(samples)}")
                if log.get('outcomes'):
                    lines.append(f"✅ Outcomes: {log.get('outcomes')}")
                followups = log.get('follow_ups')
                if followups:
                    if isinstance(followups, str):
                        import json as _j
                        try: followups = _j.loads(followups)
                        except: pass
                    if isinstance(followups, list) and followups:
                        lines.append(f"🔔 Follow-ups:")
                        for f in followups:
                            lines.append(f"  • {f}")
                lines.append(f"🕓 Saved at: {log.get('created_at','?')}")
            reply = "\n".join(lines)

    elif intent == "reminders":
        reminders = data.get("reminders", [])
        if not reminders:
            reply = "✅ No overdue follow-ups found! All HCPs are up to date."
        else:
            lines = [f"🔔 **{data.get('count', len(reminders))} HCP(s)** need follow-up attention:\n"]
            for r in reminders:
                priority = r.get("priority", "?")
                emoji = "🔴" if priority == "High" else "🟡" if priority == "Medium" else "🟢"
                lines.append(f"{emoji} **{r.get('hcp_name')}** [{priority}] — {r.get('action')} (Last: {r.get('last_date','?')})")
            reply = "\n".join(lines)

    elif intent == "sentiment":
        hcp = data.get("hcp_name", "the HCP")
        summary = data.get("trend_summary", "")
        warning = data.get("warning")
        recommendation = data.get("recommendation", "")
        reply = f"📊 **Sentiment Trend for {hcp}:**\n{summary}"
        if warning:
            reply += f"\n\n⚠️ **Warning:** {warning}"
        if recommendation:
            reply += f"\n\n💡 **Recommendation:** {recommendation}"

    elif intent == "briefing":
        hcp = data.get("hcp_name", "this HCP")
        briefing = data.get("briefing_summary", "")
        topics = data.get("key_topics", [])
        points = data.get("talking_points", [])
        followups = data.get("pending_followups", [])
        reply = f"📋 **Pre-Call Briefing for {hcp}:**\n\n{briefing}"
        if topics:
            reply += f"\n\n🗂️ **Key Topics:** {', '.join(topics)}"
        if followups:
            reply += f"\n\n📌 **Pending Follow-ups:**\n" + "\n".join(f"• {f}" for f in followups)
        if points:
            reply += f"\n\n💬 **Suggested Talking Points:**\n" + "\n".join(f"• {p}" for p in points)

    else:
        reply = "Describe your HCP interaction and I'll extract the details!"

    return {**state, "reply": reply}

# ─── Build Graph ──────────────────────────────────────────────────────────────

def build_agent():
    g = StateGraph(AgentState)

    g.add_node("detect_intent", detect_intent)
    g.add_node("execute_log", execute_log)
    g.add_node("execute_edit", execute_edit)
    g.add_node("execute_get", execute_get)
    g.add_node("execute_validate", execute_validate)
    g.add_node("execute_suggest", execute_suggest)
    g.add_node("execute_show_logs", execute_show_logs)
    g.add_node("execute_reminders", execute_reminders)
    g.add_node("execute_sentiment", execute_sentiment)
    g.add_node("execute_briefing", execute_briefing)
    g.add_node("generate_reply", generate_reply)

    g.set_entry_point("detect_intent")

    g.add_conditional_edges("detect_intent", route_intent, {
        "log":       "execute_log",
        "edit":      "execute_edit",
        "get":       "execute_get",
        "validate":  "execute_validate",
        "suggest":   "execute_suggest",
        "show_logs": "execute_show_logs",
        "reminders": "execute_reminders",
        "sentiment": "execute_sentiment",
        "briefing":  "execute_briefing",
    })

    for node in ["execute_log","execute_edit","execute_get","execute_validate","execute_suggest",
                 "execute_show_logs","execute_reminders","execute_sentiment","execute_briefing"]:
        g.add_edge(node, "generate_reply")

    g.add_edge("generate_reply", END)
    return g.compile()

_agent = None

def get_agent():
    global _agent
    if _agent is None:
        _agent = build_agent()
    return _agent

def run_agent(user_message: str, current_data: dict) -> dict:
    agent = get_agent()
    result = agent.invoke({
        "user_message": user_message,
        "current_data": current_data,
        "intent": "",
        "tool_result": {},
        "reply": ""
    })
    tool_result = result.get("tool_result") or _read_json()
    return {"reply": result["reply"], "interaction_data": tool_result}