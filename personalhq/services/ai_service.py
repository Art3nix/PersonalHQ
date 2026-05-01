"""Global service for handling interactions with Large Language Models."""

import os
import json
import time
import random
import logging
from logging.handlers import RotatingFileHandler
from datetime import timedelta
from sqlalchemy import cast, Date
from google import genai
from google.genai import types
from google.genai.errors import APIError
from personalhq.extensions import db
from personalhq.models.habits import Habit
from personalhq.models.habit_logs import HabitLog
from personalhq.models.focussessions import FocusSession, SessionStatus
from personalhq.models.braindumps import BrainDump
from personalhq.models.timebuckets import TimeBucket
from personalhq.models.dailynotes import DailyNote
from personalhq.models.journals import Journal
from personalhq.models.journalentries import JournalEntry
from personalhq.models.identities import Identity
from personalhq.services.ai_prompts import DAILY_COACH_PROMPT
from personalhq.services.time_service import get_utc_now

# --- 1. SETUP DEDICATED FILE LOGGER (ABSOLUTE PATH FIX) ---
# Dynamically find the absolute root of the project (2 folders up from this file)
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
LOG_DIR = os.path.join(ROOT_DIR, 'logs')

# Ensure the directory exists
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'system_operations.log')

sys_logger = logging.getLogger('lifehq_system')
sys_logger.setLevel(logging.INFO)

# Use the absolute LOG_FILE path we just generated
handler = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5)
formatter = logging.Formatter('[%(asctime)s] | %(levelname)s | %(message)s')
handler.setFormatter(formatter)

if not sys_logger.handlers:
    sys_logger.addHandler(handler)
    # Also output to Docker console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    sys_logger.addHandler(console_handler)
# ---------------------------------------

# The Routing Chain: Try the fastest/smartest first, then fall back to stable older models.
FALLBACK_MODELS = [
    'gemini-2.5-flash', # Primary: Fast, but prone to high-demand spikes
    'gemini-1.5-flash', # Backup 1: Older, highly stable, huge capacity
    'gemini-2.5-pro'    # Backup 2: Slower and more expensive, but different compute cluster
]

def generate_json(system_prompt, models=FALLBACK_MODELS, max_retries_per_model=3):
    """
    Sends a prompt to the AI model and strictly returns the parsed JSON response.
    Includes Exponential Backoff with Jitter and Automatic Multi-Model Fallback.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        sys_logger.error("[AI_FATAL] GEMINI_API_KEY is missing from .env")
        raise ValueError("AI configuration missing.")
        
    client = genai.Client(api_key=api_key)
    
    # 1. Loop through the Fallback Chain
    for model_name in models:
        sys_logger.info(f"[AI_INIT] Attempting AI Generation with model: {model_name}")
        
        # 2. The Retry Loop for the current model
        for attempt in range(max_retries_per_model):
            start_time = time.time()
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=system_prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                    )
                )
                
                latency_ms = round((time.time() - start_time) * 1000)
                
                # If successful, parse and return immediately
                parsed_data = json.loads(response.text)
                sys_logger.info(f"[AI_SUCCESS] Model: {model_name} | Latency: {latency_ms}ms")
                return parsed_data
                
            except APIError as e:
                latency_ms = round((time.time() - start_time) * 1000)
                # Check for 503 (High Demand) or 429 (Rate Limit)
                if e.code in [503, 429] and attempt < max_retries_per_model - 1:
                    
                    # Exponential Backoff (2s, 4s, 8s) + Random Jitter (0.0 to 1.0s)
                    sleep_time = (2 ** (attempt + 1)) + random.uniform(0, 1)
                    sys_logger.warning(f"[AI_API_ERROR] {model_name} Error ({e.code}) | Latency: {latency_ms}ms. Retrying in {sleep_time:.2f}s (Attempt {attempt + 1}/{max_retries_per_model})...")
                    
                    time.sleep(sleep_time)
                    continue # Try this specific model again
                else:
                    # We ran out of retries, or hit a fatal error (like 400 Bad Request).
                    # Break out of the retry loop so Python can fall back to the NEXT model.
                    sys_logger.error(f"[AI_MODEL_FAIL] {model_name} failed completely: {e}")
                    break 
                    
            except Exception as e:
                latency_ms = round((time.time() - start_time) * 1000)
                # Catches JSON parsing errors if the AI hallucinates the format
                sys_logger.error(f"[AI_PARSE_ERROR] {model_name} JSON format error | Latency: {latency_ms}ms | Error: {e}")
                break 

    # 3. The Fatal Catch
    # If the code escapes both loops, EVERY model in the fallback chain has failed.
    sys_logger.error("[AI_FATAL] All fallback models failed.")
    raise Exception("The AI service is experiencing global outages. Please try again later.")

def build_database_snapshot(user, logical_today):
    """Gathers a 14-day chronological snapshot of EVERY major entity in the database."""
    
    current_time = get_utc_now()
    past_14_dates = [(logical_today - timedelta(days=i)) for i in range(14, -1, -1)]
    fourteen_days_ago = past_14_dates[0]
    
    # 1. IDENTITIES
    active_identities = Identity.query.filter_by(user_id=user.id).all()
    identity_text = [f"- ID {i.id} | '{i.name}'" for i in active_identities]
    
    active_bucket = TimeBucket.query.filter(
        TimeBucket.user_id == user.id,
        TimeBucket.start_date <= logical_today,
        TimeBucket.end_date >= logical_today
    ).first()

    # 2. HABITS
    active_habits = Habit.query.filter_by(user_id=user.id, is_active=True).all()
    habit_logs = HabitLog.query.join(Habit).filter(
        Habit.user_id == user.id,
        HabitLog.completed_date >= fourteen_days_ago,
        HabitLog.completed_date <= logical_today
    ).all()
    
    habit_history_text = []
    for habit in active_habits:
        timeline = []
        for d in past_14_dates[:-1]:
            log = next((l for l in habit_logs if l.completed_date == d and l.habit_id == habit.id), None)
            # Check if progress actually met the target ---
            progress_made = getattr(log, 'progress', 0) if log else 0
            is_completed = progress_made >= habit.target_count
            timeline.append(f"{d.strftime('%a')}: {'✅' if is_completed else '❌'}")
            
        today_log = next((l for l in habit_logs if l.completed_date == logical_today and l.habit_id == habit.id), None)
        progress = getattr(today_log, 'progress', 0) if today_log else 0
        status_today = f"Done ({progress}/{habit.target_count})" if progress >= habit.target_count else f"Pending ({progress}/{habit.target_count})"
        
        habit_history_text.append(
            f"- ID {habit.id} | '{habit.name}' (Freq: {habit.frequency.name}, Target: {habit.target_count}, Trigger: '{habit.trigger}')\n"
            f"  History: [{', '.join(timeline)}]\n"
            f"  Today: {status_today}"
        )

    # 3. FOCUS SESSIONS (FIXED: target_duration_minutes & SessionStatus)
    focus_sessions = FocusSession.query.filter(
        FocusSession.user_id == user.id,
        FocusSession.target_date >= fourteen_days_ago,
        FocusSession.target_date <= logical_today
    ).all()
    
    focus_history_text = []
    for d in past_14_dates[:-1]:
        day_sessions = [s for s in focus_sessions if s.target_date == d]
        if day_sessions:
            planned_mins = sum(s.target_duration_minutes for s in day_sessions)
            actual_mins = sum(s.target_duration_minutes for s in day_sessions if s.status == SessionStatus.FINISHED)
            focus_history_text.append(f"{d.strftime('%a')}: Planned {planned_mins}m, Done {actual_mins}m")
            
    today_focus = [s for s in focus_sessions if s.target_date == logical_today]
    today_focus_text = [
        f"- ID {s.id} | {s.target_duration_minutes}m ({'Done' if s.status == SessionStatus.FINISHED else 'Pending'})" 
        for s in today_focus
    ]

    # 4. JOURNALS
    active_journals = Journal.query.filter_by(user_id=user.id).all()
    journal_entries = JournalEntry.query.join(Journal).filter(
        Journal.user_id == user.id,
        cast(JournalEntry.created_at, Date) >= fourteen_days_ago
    ).all()
    
    journal_history_text = []
    for journal in active_journals:
        entries = [e for e in journal_entries if e.journal_id == journal.id]
        entry_dates = [e.created_at.strftime('%a') for e in entries if e.created_at]
        journal_history_text.append(
            f"- ID {journal.id} | '{journal.name}' (Freq: {journal.frequency.name})\n"
            f"  Entries Last 14 Days: {', '.join(entry_dates) if entry_dates else 'None'}"
        )

    # 5. BRAINDUMPS / INBOX (FIXED: processed column)
    open_loops = BrainDump.query.filter(
        BrainDump.user_id == user.id,
        (BrainDump.processed.is_(False) | BrainDump.processed.is_(None))
    ).count()
    
    recently_processed = BrainDump.query.filter(
        BrainDump.user_id == user.id, 
        BrainDump.processed.is_(True),
        cast(BrainDump.created_at, Date) >= fourteen_days_ago
    ).count()

    # Assemble the Master String
    snapshot_string = f"""
    --- SYSTEM CLOCK & LIFELINE ---
    Current Logical Date: {logical_today.strftime('%A, %B %d')}
    Exact Current Time: {current_time.strftime('%I:%M %p')}
    Current Time Bucket: {active_bucket.name + f' (ID: {active_bucket.id})' if active_bucket else "None defined"}
    
    --- 14-DAY CHRONOLOGICAL PATTERNS ---
    IDENTITIES:
    {chr(10).join(identity_text) if identity_text else "- None."}

    HABITS:
    {chr(10).join(habit_history_text) if habit_history_text else "- No active habits."}
    
    FOCUS SESSIONS:
    14-Day Map: {', '.join(focus_history_text) if focus_history_text else "No past focus data."}
    Today's Planned:
    {chr(10).join(today_focus_text) if today_focus_text else "- None."}
    
    JOURNALS:
    {chr(10).join(journal_history_text) if journal_history_text else "- No active journals."}
    
    --- SYSTEM HEALTH & LOAD ---
    Inbox/Brain Dumps: {open_loops} open loops. ({recently_processed} processed in last 14 days).
    """
    return snapshot_string

def generate_daily_context(user, logical_date_to_prep):
    """Feeds the DB snapshot to the AI to generate layered, encouraging coaching text."""
    
    # Check if we already generated a note for today so we don't spam the API
    existing_note = DailyNote.query.filter_by(user_id=user.id, logical_date=logical_date_to_prep).first()
    if existing_note:
        sys_logger.info(f"[COACH_SKIPPED] Daily note already exists for {user.email} on {logical_date_to_prep}")
        return existing_note

    sys_logger.info(f"[COACH_START] Generating daily context for {user.email} for {logical_date_to_prep}")
    
    daily_data = build_database_snapshot(user, logical_date_to_prep)
    
    system_prompt = f"""
{DAILY_COACH_PROMPT}

{daily_data}

TASK: 
Act as a modern, collaborative performance coach. Review the user's 14-day history and generate highly targeted, practical coaching text.

INSTRUCTIONS:
1. MANDATORY FIELDS: You MUST ALWAYS generate text for the global `ai_daily_briefing` and ALL `_subtitle` fields. These set the daily tone and cannot be null.
2. EMPTY STATES: ONLY generate text for `_empty_state` fields if the database snapshot explicitly shows that the user has ZERO items in that category. If they have active items, the empty state field MUST be `null`.
3. BALANCED DISTRIBUTION: For Time Buckets, Journals, and Focus Sessions, generate insights for a MAXIMUM of 2 to 3 items. For Habits, generate data for the majority of them, but intentionally leave a few completely blank (omit them from the JSON array) so the coaching feels organic and not overwhelming.
4. HABIT ALGORITHM: Generate both `ai_insight` (Pre-action advice) and `ai_celebration` (Post-action praise) using this deterministic logic:
   - NO MAD LIBS: NEVER use formulaic, repetitive phrases like "To be 'Identity', you must do X." Do NOT put identity names in apostrophes or quotes.
   - BE CREATIVE & SPECIFIC: Make the text deeply encouraging and intimately specific to the habit's actual action (e.g., if the habit is reading, talk about pages, ideas, or expanding the mind, not just "doing the habit").
   - If they missed yesterday: Insight warns about sliding; Celebration praises the recovery.
   - If on a streak: Insight reminds them of momentum; Celebration hypes up the specific streak number.
   - If at an all-time best: Insight hypes the record; Celebration focuses on the new milestone.
   - If 0 streak: Insight pushes the 2-minute rule to just start; Celebration congratulates taking the first step.
5. NO COMMANDING: Guide and challenge the user gently. Do not issue aggressive demands.

You MUST respond with a RAW, valid JSON OBJECT using this exact schema:

{{
  "daily_note": {{
    // --- DASHBOARD (Global Coach) ---
    "ai_daily_briefing": "[MANDATORY] Direct, supportive coaching based on their 14-day reality. Offer a collaborative game plan for today. (15-25 words)",
    "ai_focus_empty_state": "[CONDITIONAL] Suggest scheduling a session ONLY if focus queue is empty. (Max 15 words)",
    "ai_habit_empty_state": "[CONDITIONAL] Encourage them to cast a vote for their identity ONLY if they have zero habits. (Max 15 words)",
    "ai_chapter_empty_state": "[CONDITIONAL] Remind them to define this decade ONLY if no time buckets exist. (Max 15 words)",

    // --- INBOX / BRAINDUMPS ---
    "ai_inbox_subtitle": "[MANDATORY] A general observation about their current mental load. (Max 15 words)",
    "ai_inbox_overload": "[OPTIONAL] Supportive intervention ONLY if they have >10 open loops. Otherwise null. (Max 15 words)",
    "ai_braindump_empty_state": "[CONDITIONAL] Acknowledge they have a clear mind ONLY if inbox is empty. (Max 15 words)",

    // --- DEEP WORK / PLANNER ---
    "ai_planner_subtitle": "[MANDATORY] Practical advice about today's scheduled focus workload or the value of deep work. (Max 15 words)",
    "ai_planner_empty_state": "[CONDITIONAL] Challenge them to block out time ONLY if no sessions exist today. (Max 15 words)",
    "ai_focus_analysis": "[OPTIONAL] Analyze their 14-day focus trend. Point out consistency or inconsistency. (Max 20 words)",

    // --- HABITS ---
    "ai_habits_subtitle": "[MANDATORY] A modern note about how their habits prove their identity. (Max 15 words)",
    "ai_habits_empty_state": "[CONDITIONAL] Suggest lowering the friction to 2 minutes ONLY if zero habits exist. (Max 15 words)",
    "ai_heatmap_analysis": "[OPTIONAL] Call out their 14-day record. Praise consistency or gently point out missing days. (Max 20 words)",
    "ai_dow_analysis": "[OPTIONAL] Point out specific day-of-week patterns plainly. (Max 20 words)",
    "ai_momentum_analysis": "[OPTIONAL] Leverage their streaks or lack thereof to encourage action today. (Max 20 words)",

    // --- IDENTITIES ---
    "ai_identity_empty_state": "[CONDITIONAL] Ask them who they want to become ONLY if no identities exist. (Max 15 words)",

    // --- JOURNALS ---
    "ai_journals_subtitle": "[MANDATORY] A practical note about clearing their head through writing. (Max 15 words)",
    "ai_journals_empty_state": "[CONDITIONAL] Prompt them to create a space to write ONLY if zero journals exist. (Max 15 words)",
    "ai_writing_coach": "[OPTIONAL] Warm encouragement shown while they type an entry today. (Max 15 words)",
    "ai_prompt_suggestion": "[OPTIONAL] A highly specific, practical question they should answer based on recent behavior. (Max 20 words)",
    "ai_archive_insight": "[OPTIONAL] An observation about their historical writing patterns. (Max 20 words)",
    "ai_archive_empty_state": "[CONDITIONAL] Encourage them to log their first entry ONLY if the archive is empty. (Max 15 words)",

    // --- TIME BUCKETS (LIFE MAP) ---
    "ai_map_subtitle": "[MANDATORY] A reminder about maximizing experiences before they get too old. (Max 20 words)",
    "ai_lifemap_empty_state": "[CONDITIONAL] Tell them to map out their decades ONLY if the map is empty. (Max 20 words)"
  }},
  
  "entity_updates": {{
    // [CATEGORY CAPS]: Pick a maximum of 2 to 3 items per array below. Leave the rest out.
    "time_buckets": [ {{ "id": 123, "ai_insight": "[Item Coach] Specific coaching for this decade.", "ai_empty_state": "Max 15 words." }} ],
    "journals": [ {{ "id": 123, "ai_insight": "[Item Coach] Specific coaching for this journal." }} ],
    "identities": [ {{ "id": 123, "ai_insight": "[Item Coach] Supportive check: Do recent actions align with this specific identity?" }} ],
    "focus_sessions": [ {{ "id": 123, "ai_insight": "[Item Coach] Highly specific coaching for THIS exact session.", "ai_intention": "Max 15 words." }} ],
    "habits": [ 
      {{ 
        "id": 123, 
        "ai_insight": "[PRE-ACTION] Insight to read BEFORE doing the habit.", 
        "ai_celebration": "[POST-ACTION] Praise to read AFTER completing it." 
      }} 
    ]
  }}
}}
"""

    sys_logger.info(f"[COACH_PROMPT_SENT] Sending data snapshot to AI for {user.email}.")
    try:
        ai_data = generate_json(system_prompt)
        sys_logger.info(f"[COACH_RESPONSE_RECEIVED] Successfully parsed JSON for {user.email}.")
        
        # --- 1. PROCESS DAILY NOTE (GLOBAL) ---
        note_data = ai_data.get('daily_note', {})
        daily_note = DailyNote.query.filter_by(user_id=user.id, logical_date=logical_date_to_prep).first()
        if not daily_note:
            daily_note = DailyNote(user_id=user.id, logical_date=logical_date_to_prep)
            db.session.add(daily_note)
            
        # Dashboard
        daily_note.ai_daily_briefing = note_data.get('ai_daily_briefing')
        daily_note.ai_focus_empty_state = note_data.get('ai_focus_empty_state')
        daily_note.ai_habit_empty_state = note_data.get('ai_habit_empty_state')
        daily_note.ai_chapter_empty_state = note_data.get('ai_chapter_empty_state')
        
        # Braindumps
        daily_note.ai_inbox_subtitle = note_data.get('ai_inbox_subtitle')
        daily_note.ai_inbox_overload = note_data.get('ai_inbox_overload')
        daily_note.ai_braindump_empty_state = note_data.get('ai_braindump_empty_state')
        
        # Deep Work
        daily_note.ai_planner_subtitle = note_data.get('ai_planner_subtitle')
        daily_note.ai_planner_empty_state = note_data.get('ai_planner_empty_state')
        daily_note.ai_focus_analysis = note_data.get('ai_focus_analysis')
        
        # Habits
        daily_note.ai_habits_subtitle = note_data.get('ai_habits_subtitle')
        daily_note.ai_habits_empty_state = note_data.get('ai_habits_empty_state')
        daily_note.ai_heatmap_analysis = note_data.get('ai_heatmap_analysis')
        daily_note.ai_dow_analysis = note_data.get('ai_dow_analysis')
        daily_note.ai_momentum_analysis = note_data.get('ai_momentum_analysis')
        
        # Identity
        daily_note.ai_identity_empty_state = note_data.get('ai_identity_empty_state')
        
        # Journals
        daily_note.ai_journals_subtitle = note_data.get('ai_journals_subtitle')
        daily_note.ai_journals_empty_state = note_data.get('ai_journals_empty_state')
        daily_note.ai_writing_coach = note_data.get('ai_writing_coach')
        daily_note.ai_prompt_suggestion = note_data.get('ai_prompt_suggestion')
        daily_note.ai_archive_insight = note_data.get('ai_archive_insight')
        daily_note.ai_archive_empty_state = note_data.get('ai_archive_empty_state')
        
        # Time Buckets
        daily_note.ai_map_subtitle = note_data.get('ai_map_subtitle')
        daily_note.ai_lifemap_empty_state = note_data.get('ai_lifemap_empty_state')
        
        # --- 2. PROCESS TARGETED ENTITY UPDATES ---
        updates = ai_data.get('entity_updates', {})
        
        # Add this new Habit block:
        for h_update in updates.get('habits', []):
            h = db.session.get(Habit, h_update.get('id'))
            if h and h.user_id == user.id:
                if 'ai_insight' in h_update: h.ai_insight = h_update.get('ai_insight')
                if 'ai_celebration' in h_update: h.ai_celebration = h_update.get('ai_celebration')
        
        for tb_update in updates.get('time_buckets', []):
            tb = db.session.get(TimeBucket, tb_update.get('id'))
            if tb and tb.user_id == user.id:
                if 'ai_insight' in tb_update: tb.ai_insight = tb_update.get('ai_insight')
                if 'ai_empty_state' in tb_update: tb.ai_empty_state = tb_update.get('ai_empty_state')
                
        for j_update in updates.get('journals', []):
            j = db.session.get(Journal, j_update.get('id'))
            if j and j.user_id == user.id:
                if 'ai_insight' in j_update: j.ai_insight = j_update.get('ai_insight')
                
        for i_update in updates.get('identities', []):
            ident = db.session.get(Identity, i_update.get('id'))
            if ident and ident.user_id == user.id:
                if 'ai_insight' in i_update: ident.ai_insight = i_update.get('ai_insight')
                
        for fs_update in updates.get('focus_sessions', []):
            fs = db.session.get(FocusSession, fs_update.get('id'))
            if fs and fs.user_id == user.id:
                if 'ai_insight' in fs_update: fs.ai_insight = fs_update.get('ai_insight')
                if 'ai_intention' in fs_update: fs.ai_intention = fs_update.get('ai_intention')

        db.session.commit()
        sys_logger.info(f"[COACH_COMPLETE] Successfully updated DB with AI insights for {user.email}.")
        return daily_note
        
    except Exception as e:
        db.session.rollback()
        sys_logger.error(f"[COACH_DB_ERROR] Daily Context Generation Error for {user.email}: {e}")
        return None