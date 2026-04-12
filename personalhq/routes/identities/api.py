"""API routes for Identity Matrix actions."""

from datetime import timedelta, date
from flask import Blueprint, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from personalhq.extensions import db
from personalhq.models.identities import Identity
from personalhq.models.journals import Journal, JournalFrequency
from personalhq.models.journalprompts import JournalPrompt
from personalhq.models.habits import Habit, HabitFrequency
from personalhq.models.timebuckets import TimeBucket
from personalhq.models.bucket_experience import BucketExperience
from personalhq.models.experiences import Experience
from personalhq.models.coretheme import CoreTheme
from personalhq.models.emotionalvalue import EmotionalValue
from personalhq.services.time_service import get_logical_today
from personalhq.services.ai_service import generate_json
from personalhq.services.ai_prompts import SYSTEM_ARCHITECT_PROMPT

identities_api_bp = Blueprint('identities_api', __name__, url_prefix='/actions/identities')

@identities_api_bp.route('/create', methods=['POST'])
@login_required
def create_identity():
    """Creates a new Identity and optionally links existing unassigned habits."""
    name = request.form.get('name')
    description = request.form.get('description')
    color = request.form.get('color', 'stone')

    # getlist() captures all checked checkboxes sharing the 'habit_ids' name
    habit_ids = request.form.getlist('habit_ids')

    if not name:
        flash('Identity name is required.', 'error')
        return redirect(url_for('identities_view.matrix'))

    new_identity = Identity(
        user_id=current_user.id,
        name=name.strip(),
        description=description.strip() if description else None,
        color=color
    )

    db.session.add(new_identity)
    db.session.flush() # Flush to generate the new_identity.id without committing yet

    # If the user checked any unassigned habits in the modal, update their foreign keys
    if habit_ids:
        habits_to_update = Habit.query.filter(
            Habit.id.in_(habit_ids), 
            Habit.user_id == current_user.id,
            Habit.is_active == True
        ).all()

        for habit in habits_to_update:
            habit.identity_id = new_identity.id

    db.session.commit()
    flash(f'Identity "{new_identity.name}" established.', 'success')

    return redirect(url_for('identities_view.matrix'))

@identities_api_bp.route('/<int:identity_id>/edit', methods=['POST'])
@login_required
def edit_identity(identity_id):
    """Updates an existing Identity's core details."""
    identity = db.session.get(Identity, identity_id)
    
    if not identity or identity.user_id != current_user.id:
        return redirect(url_for('identities_view.matrix'))

    name = request.form.get('name')
    description = request.form.get('description')
    color = request.form.get('color', 'stone')

    if name:
        identity.name = name.strip()
        identity.description = description.strip() if description else None
        identity.color = color
        db.session.commit()
        flash(f'Identity "{identity.name}" updated.', 'success')

    return redirect(url_for('identities_view.matrix'))

@identities_api_bp.route('/<int:identity_id>/delete', methods=['POST'])
@login_required
def delete_identity(identity_id):
    """Deletes an Identity and safely unassigns its associated habits and focus sessions."""
    identity = db.session.get(Identity, identity_id)

    if identity and identity.user_id == current_user.id:
        name = identity.name
        for habit in identity.habits:
            habit.identity_id = None
        for session in identity.focus_sessions:
            session.identity_id = None
        db.session.delete(identity)
        db.session.commit()
        flash(f'Identity "{name}" deleted.', 'success')

    return redirect(url_for('identities_view.matrix'))

@identities_api_bp.route('/generate_batch', methods=['POST'])
@login_required
def generate_batch():
    """Takes MULTIPLE identities from onboarding, architects the whole system dynamically, and saves it."""
    data = request.get_json()
    identities_input = data.get('identities', [])
    
    if not identities_input or len(identities_input) == 0:
        return jsonify({"status": "error", "message": "At least one identity is required."}), 400

    identities_text = "\n".join([f"- '{req['name']}': {req['description']}" for req in identities_input])

    # --- NEW: Calculate current age ---
    today = get_logical_today(current_user)
    age_context = "Assume the user is in their late 20s." # Fallback
    if current_user.date_of_birth:
        current_age = today.year - current_user.date_of_birth.year - ((today.month, today.day) < (current_user.date_of_birth.month, current_user.date_of_birth.day))
        age_context = f"The user is currently {current_age} years old."

    # Update the prompt string:
    system_prompt = f"""
{SYSTEM_ARCHITECT_PROMPT}

TASK: 
The user is committing to a completely new lifestyle based on multiple identities.
{age_context}

Here are the identities they are claiming:
{identities_text}

INSTRUCTIONS:
Your job is to build a psychological and operational system to support this new lifestyle.
YOU are in complete control of the system's architecture. 

- Generate 1-3 global Time Buckets based on the "Die With Zero" philosophy. Assign specific age ranges to these buckets based on the user's current age. Generate 2-4 compelling EXPERIENCES inside each bucket.
- Generate 1-3 global Journals for compartmentalization. Determine how often they should be used.
- For EACH identity provided, select an appropriate color, and generate 1-3 highly actionable Habits. Determine their frequency, target counts, and break them down using the 4 Laws of Behavior Change.

You MUST respond with a RAW, valid JSON OBJECT using this exact structure. Do NOT include markdown blocks.

{{
  "time_buckets": [
    {{
      "name": "Name of a decade/life chapter (e.g., 'The Foundation Years')",
      "theme": "A short phrase describing the focus",
      "start_age": 25, // Integer
      "end_age": 35, // Integer
      "experiences": [
        {{
          "name": "A specific, memorable experience",
          "details": "Why this creates a lasting Memory Dividend",
          "core_theme": "A single word category (e.g., 'Adventure', 'Health', 'Career')",
          "theme_color": "A valid tailwind color for the theme",
          "emotional_value": "The core feeling (e.g., 'Awe', 'Connection', 'Pride')",
          "emotion_color": "A valid tailwind color for the emotion"
        }}
      ]
    }}
  ],
  "journals": [
    {{
      "name": "Specific journal name",
      "description": "Purpose of this space",
      "icon": "book-open",
      "color": "emerald",
      "frequency": "Must be exactly 'daily', 'weekly', or 'monthly'",
      "prompts": [
        "A deep reflection question",
        "An action-oriented Next Action question"
      ]
    }}
  ],
  "identities": [
    {{
      "name": "The EXACT identity name provided by the user",
      "color": "indigo",
      "habits": [
        {{
          "name": "Short, verb-driven habit (2-Minute Rule)",
          "description": "Why this proves the identity",
          "icon": "target",
          "frequency": "Must be exactly 'daily' or 'weekly'",
          "target_count": 1, 
          "trigger": "The exact physical cue",
          "craving": "How to make the action attractive",
          "reward": "The immediate satisfying payoff"
        }}
      ]
    }}
  ]
}}

Valid colors: slate, gray, zinc, neutral, stone, red, orange, amber, yellow, lime, green, emerald, teal, cyan, sky, blue, indigo, violet, purple, fuchsia, pink, rose.
Use valid Lucide icon names.
"""

    try:
        ai_data = generate_json(system_prompt)
        
        # 1. Create Identities first so we have their Database IDs
        identity_map = {}
        for req in identities_input:
            new_id = Identity(
                user_id=current_user.id,
                name=req['name'].strip(),
                description=req['description'].strip() if req.get('description') else None
            )
            db.session.add(new_id)
            db.session.flush()
            identity_map[req['name'].strip().lower()] = new_id

        # 2. Process Time Buckets AND their nested Experiences
        for tb_data in ai_data.get('time_buckets', []):
            
            start_date = get_logical_today(current_user)
            end_date = start_date + timedelta(days=3650) # Fallback
            
            if current_user.date_of_birth and 'start_age' in tb_data and 'end_age' in tb_data:
                dob = current_user.date_of_birth
                start_age = int(tb_data['start_age'])
                end_age = int(tb_data['end_age'])
                
                # Start Date: Their birthday on the year they turn start_age
                try:
                    start_date = date(dob.year + start_age, dob.month, dob.day)
                except ValueError:
                    start_date = date(dob.year + start_age, 2, 28) # Leap year catch
                
                # End Date: The day before they turn (end_age + 1)
                try:
                    next_bday = date(dob.year + end_age + 1, dob.month, dob.day)
                except ValueError:
                    next_bday = date(dob.year + end_age + 1, 2, 28)
                end_date = next_bday - timedelta(days=1)

            new_bucket = TimeBucket(
                user_id=current_user.id,
                name=tb_data['name'],
                theme=tb_data['theme'],
                start_date=start_date,
                end_date=end_date
            )
            db.session.add(new_bucket)
            db.session.flush()
            
            # --- PROCESS EXPERIENCES (With Association Table) ---
            for exp_data in tb_data.get('experiences', []):
                
                # Get or Create Core Theme ONLY if provided
                theme_id = None
                theme_name = exp_data.get('core_theme')
                if theme_name:
                    theme_color = exp_data.get('theme_color', 'stone')
                    core_theme = CoreTheme.query.filter_by(user_id=current_user.id, name=theme_name).first()
                    if not core_theme:
                        core_theme = CoreTheme(user_id=current_user.id, name=theme_name, color=theme_color)
                        db.session.add(core_theme)
                        db.session.flush()
                    theme_id = core_theme.id
                
                # Get or Create Emotional Value ONLY if provided
                emotion_id = None
                emotion_name = exp_data.get('emotional_value')
                if emotion_name:
                    emotion_color = exp_data.get('emotion_color', 'rose')
                    emotional_value = EmotionalValue.query.filter_by(user_id=current_user.id, name=emotion_name).first()
                    if not emotional_value:
                        emotional_value = EmotionalValue(user_id=current_user.id, name=emotion_name, color=emotion_color)
                        db.session.add(emotional_value)
                        db.session.flush()
                    emotion_id = emotional_value.id

                # 1. Create the base Experience (Do not pass time_bucket_id here!)
                new_experience = Experience(
                    # Depending on your model, include user_id=current_user.id if Experiences are tied to users
                    name=exp_data['name'],
                    details=exp_data.get('details'),
                    theme_id=theme_id,             
                    emotional_value_id=emotion_id  
                )
                db.session.add(new_experience)
                db.session.flush() # Flush to get new_experience.id

                # 2. Link the Experience to the Time Bucket using the Junction Table
                link = BucketExperience(
                    bucket_id=new_bucket.id,
                    experience_id=new_experience.id
                )
                db.session.add(link)

        # 3. Process Journals (With AI-Controlled Frequency)
        for j_data in ai_data.get('journals', []):
            
            # Map the AI's text response safely to your Enum
            ai_freq = j_data.get('frequency', '').lower()
            if 'week' in ai_freq:
                j_freq = JournalFrequency.WEEKLY
            elif 'month' in ai_freq:
                j_freq = JournalFrequency.MONTHLY
            else:
                j_freq = JournalFrequency.DAILY
                
            new_journal = Journal(
                user_id=current_user.id,
                name=j_data['name'],
                description=j_data.get('description'),
                icon=j_data['icon'],
                color=j_data['color'],
                frequency=j_freq
            )
            db.session.add(new_journal)
            db.session.flush()

            for prompt_text in j_data.get('prompts', []):
                new_prompt = JournalPrompt(
                    journal_id=new_journal.id,
                    text=prompt_text
                )
                db.session.add(new_prompt)

        # 4. Process Identities and Habits (With AI-Controlled Targets)
        for id_data in ai_data.get('identities', []):
            identity_name = id_data['name'].strip().lower()
            identity_obj = identity_map.get(identity_name)
            
            if identity_obj:
                if 'color' in id_data:
                    identity_obj.color = id_data['color']
                
                for habit_data in id_data.get('habits', []):
                    
                    # --- THE FIX: Map the AI string to the Enum ---
                    ai_habit_freq = habit_data.get('frequency', '').upper()
                    if 'WEEK' in ai_habit_freq:
                        h_freq = HabitFrequency.WEEKLY
                    else:
                        h_freq = HabitFrequency.DAILY
                    
                    new_habit = Habit(
                        user_id=current_user.id,
                        identity_id=identity_obj.id, 
                        name=habit_data['name'],
                        description=habit_data.get('description'),
                        icon=habit_data['icon'],
                        
                        # Use the safely mapped Enum!
                        frequency=h_freq,
                        target_count=habit_data.get('target_count', 1), 
                        is_active=True,
                        
                        trigger=habit_data.get('trigger', ''),
                        craving=habit_data.get('craving', ''),
                        reward=habit_data.get('reward', '')
                    )
                    db.session.add(new_habit)

        db.session.commit()
        return jsonify({"status": "success"}), 200

    except ValueError as ve:
        return jsonify({"status": "error", "message": str(ve)}), 500
    except Exception as e:
        db.session.rollback()
        print(f"AI Batch Generation Error: {e}")
        return jsonify({"status": "error", "message": "Failed to generate system. Please try again."}), 500
