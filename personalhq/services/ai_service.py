"""Global service for handling interactions with Large Language Models."""

import os
import json
import time
import random
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
        print("CRITICAL: GEMINI_API_KEY is missing from .env")
        raise ValueError("AI configuration missing.")
        
    client = genai.Client(api_key=api_key)
    
    # 1. Loop through the Fallback Chain
    for model_name in models:
        print(f"Attempting AI Generation with model: {model_name}")
        
        # 2. The Retry Loop for the current model
        for attempt in range(max_retries_per_model):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=system_prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                    )
                )
                
                # If successful, parse and return immediately
                return json.loads(response.text)
                
            except APIError as e:
                # Check for 503 (High Demand) or 429 (Rate Limit)
                if e.code in [503, 429] and attempt < max_retries_per_model - 1:
                    
                    # Exponential Backoff (2s, 4s, 8s) + Random Jitter (0.0 to 1.0s)
                    sleep_time = (2 ** (attempt + 1)) + random.uniform(0, 1)
                    print(f"{model_name} API Error ({e.code}). Retrying in {sleep_time:.2f}s (Attempt {attempt + 1}/{max_retries_per_model})...")
                    
                    time.sleep(sleep_time)
                    continue # Try this specific model again
                else:
                    # We ran out of retries, or hit a fatal error (like 400 Bad Request).
                    # Break out of the retry loop so Python can fall back to the NEXT model.
                    print(f"{model_name} failed completely: {e}")
                    break 
                    
            except Exception as e:
                # Catches JSON parsing errors if the AI hallucinates the format
                print(f"{model_name} JSON format error: {e}")
                break 

    # 3. The Fatal Catch
    # If the code escapes both loops, EVERY model in the fallback chain has failed.
    print("FATAL: All fallback models failed.")
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
    """Feeds the DB snapshot to the AI to generate global context and targeted entity insights."""
    
    daily_data = build_database_snapshot(user, logical_date_to_prep)
    
    system_prompt = f"""
{DAILY_COACH_PROMPT}

{daily_data}

TASK: 
Act as a personal performance coach. Review the user's 14-day history and give them direct, actionable, text-message-style coaching.

COACHING DIRECTIVES:
1. Speak directly to the user ("You", "Your"). Never use third-person ("The user", "Businessman identity").
2. No Cold Data: Never just state facts like "No entries" or "Habit execution stalled." Give them the "So what?" and a clear next step.
3. Conversational Nudges: Instead of "Reflect on gratitude," say something like: "You haven't written in a few days. Take 2 minutes right now to drop a single bullet point and clear your head."
4. Be firm but empathetic. Tell them to scale down if they are struggling.

INSTRUCTIONS:
- SPARCE GENERATION: Do NOT fill every field. Only generate an insight if it is HIGHLY RELEVANT right now.
- If an entity does not urgently need coaching today, DO NOT include its ID in the entity_updates.

You MUST respond with a RAW, valid JSON OBJECT:

{{
  "daily_note": {{
    "ai_daily_briefing": "15-25 words. Conversational coaching based on their trends. Give them a game plan for today.",
    
    "ai_focus_empty_state": "Max 10 words. Friendly nudge to plan a session.",
    "ai_habit_empty_state": "Max 10 words. Direct advice to create their first habit.",
    "ai_inbox_subtitle": "Max 10 words. E.g., 'Let's clear the noise.'",
    "ai_inbox_overload": "Max 15 words. Firm coaching to process their massive backlog.",
    "ai_braindump_empty_state": "Max 15 words. Remind them to dump thoughts here.",
    "ai_planner_subtitle": "Max 10 words. E.g., 'Protect your time.'",
    "ai_planner_empty_state": "Max 10 words. Actionable nudge to schedule deep work.",
    "ai_journal_subtitle": "Max 10 words. E.g., 'Clear your mind.'",
    "ai_journal_empty_state": "Max 10 words. Friendly prompt to create a journal.",
    "ai_map_subtitle": "Max 15 words. Casual reminder about their current Life Chapter.",
    "ai_chapter_empty_state": "Max 15 words. Nudge to define this decade.",
    "ai_lifemap_empty_state": "Max 15 words. Nudge to build their timeline."
  }},
  
  "entity_updates": {{
    "time_buckets": [ 
      {{ "id": 123, "ai_insight": "Max 15 words. Casual coaching note.", "ai_empty_state": "Max 15 words. Actionable advice." }} 
    ],
    "journals": [ {{ "id": 123, "ai_insight": "Max 15 words. Conversational writing prompt based on their habits." }} ],
    "identities": [ {{ "id": 123, "ai_insight": "Max 15 words. Real-talk about whether their habits match this identity." }} ],
    "focus_sessions": [ {{ "id": 123, "ai_insight": "Max 15 words.", "ai_intention": "Max 10 words." }} ]
  }}
}}
"""
    print(system_prompt)
    try:
        ai_data = generate_json(system_prompt)
        print(ai_data)
        
        # --- 1. PROCESS DAILY NOTE (GLOBAL) ---
        note_data = ai_data.get('daily_note', {})
        daily_note = DailyNote.query.filter_by(user_id=user.id, logical_date=logical_date_to_prep).first()
        if not daily_note:
            daily_note = DailyNote(user_id=user.id, logical_date=logical_date_to_prep)
            db.session.add(daily_note)
            
        # mapping removed the non-existent title
        daily_note.ai_daily_briefing = note_data.get('ai_daily_briefing')
        daily_note.ai_focus_empty_state = note_data.get('ai_focus_empty_state')
        daily_note.ai_habit_empty_state = note_data.get('ai_habit_empty_state')
        daily_note.ai_inbox_subtitle = note_data.get('ai_inbox_subtitle')
        daily_note.ai_inbox_overload = note_data.get('ai_inbox_overload')
        daily_note.ai_braindump_empty_state = note_data.get('ai_braindump_empty_state')
        daily_note.ai_planner_subtitle = note_data.get('ai_planner_subtitle')
        daily_note.ai_planner_empty_state = note_data.get('ai_planner_empty_state')
        daily_note.ai_journal_subtitle = note_data.get('ai_journal_subtitle')
        daily_note.ai_journal_empty_state = note_data.get('ai_journal_empty_state')
        daily_note.ai_map_subtitle = note_data.get('ai_map_subtitle')
        daily_note.ai_chapter_empty_state = note_data.get('ai_chapter_empty_state')
        daily_note.ai_lifemap_empty_state = note_data.get('ai_lifemap_empty_state')
        
        # --- 2. PROCESS TARGETED ENTITY UPDATES ---
        updates = ai_data.get('entity_updates', {})
        
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
        return daily_note
        
    except Exception as e:
        db.session.rollback()
        print(f"Daily Context Generation Error: {e}")
        return None
