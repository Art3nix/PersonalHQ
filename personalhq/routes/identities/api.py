"""API routes for Identity Matrix actions."""

from datetime import timedelta
from flask import Blueprint, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from personalhq.extensions import db
from personalhq.models.identities import Identity
from personalhq.models.journals import Journal, JournalFrequency
from personalhq.models.journalprompts import JournalPrompt
from personalhq.models.habits import Habit
from personalhq.models.timebuckets import TimeBucket
from personalhq.services.time_service import get_local_today
from personalhq.services.ai_service import generate_json

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
    """Takes MULTIPLE identities from onboarding, architects the whole system, and saves it."""
    data = request.get_json()
    identities_input = data.get('identities', [])
    
    if not identities_input or len(identities_input) == 0:
        return jsonify({"status": "error", "message": "At least one identity is required."}), 400

    # Format the user's inputs into a readable string for the LLM
    identities_text = "\n".join([f"Identity {i}: '{req['name']}' - Vision: '{req['description']}'" for i, req in enumerate(identities_input)])

    system_prompt = f"""
You are an elite performance coach and system architect. 
The user is committing to a completely new lifestyle based on multiple identities.

Here are the identities they are claiming:
{identities_text}

Your job is to build a psychological and operational system to support EACH of these identities.
You MUST respond with a RAW, valid JSON ARRAY containing an object for each identity in the exact order they were provided. Do NOT include markdown blocks.

Use this exact structure (Return an ARRAY of these objects):
[
  {{
    "habit": {{
      "name": "Short, verb-driven habit",
      "description": "Why this proves the identity",
      "icon": "target"
    }},
    "time_bucket": {{
      "name": "Name of a decade/life chapter (e.g., 'The Foundation Years')",
      "theme": "A short phrase describing the focus"
    }},
    "journal": {{
      "name": "Specific journal name",
      "description": "Purpose of this space",
      "icon": "book-open",
      "color": "emerald",
      "prompts": [
        "A deep reflection question",
        "An action-oriented growth question"
      ]
    }}
  }}
]

Valid colors: slate, gray, zinc, neutral, stone, red, orange, amber, yellow, lime, green, emerald, teal, cyan, sky, blue, indigo, violet, purple, fuchsia, pink, rose.
Use valid Lucide icon names.
"""

    try:
        # One clean call to the global service. We get a list back directly.
        ai_data_list = generate_json(system_prompt)
        
        # Loop through the user's inputs and the AI's outputs simultaneously
        for i, req in enumerate(identities_input):
            ai_data = ai_data_list[i]
            
            # 1. Core Identity
            new_id = Identity(
                user_id=current_user.id,
                name=req['name'].strip(),
                description=req['description'].strip() if req.get('description') else None
            )
            db.session.add(new_id)
            db.session.flush() # Flush to get new_id.id
            
            # 2. Habit
            new_habit = Habit(
                user_id=current_user.id,
                identity_id=new_id.id, 
                name=ai_data['habit']['name'],
                description=ai_data['habit']['description'],
                icon=ai_data['habit']['icon']
            )
            db.session.add(new_habit)
            
            # 3. Time Bucket
            start_date = get_local_today()
            try:
                end_date = start_date.replace(year=start_date.year + 10)
            except ValueError:
                end_date = start_date + timedelta(days=3650)

            new_bucket = TimeBucket(
                user_id=current_user.id,
                name=ai_data['time_bucket']['name'],
                theme=ai_data['time_bucket']['theme'],
                start_date=start_date,
                end_date=end_date
            )
            db.session.add(new_bucket)
            
            # 4. Journal
            new_journal = Journal(
                user_id=current_user.id,
                name=ai_data['journal']['name'],
                description=ai_data['journal']['description'],
                icon=ai_data['journal']['icon'],
                color=ai_data['journal']['color'],
                frequency=JournalFrequency.DAILY
            )
            db.session.add(new_journal)
            db.session.flush() 
            
            # 5. Prompts
            for prompt_text in ai_data['journal']['prompts']:
                new_prompt = JournalPrompt(
                    journal_id=new_journal.id,
                    text=prompt_text
                )
                db.session.add(new_prompt)
                
        # Commit the entire batch!
        db.session.commit()
        
        return jsonify({"status": "success"}), 200

    except ValueError as ve:
        return jsonify({"status": "error", "message": str(ve)}), 500
    except Exception as e:
        db.session.rollback()
        print(f"AI Batch Generation Error: {e}")
        return jsonify({"status": "error", "message": "Failed to generate system. Please try again."}), 500
