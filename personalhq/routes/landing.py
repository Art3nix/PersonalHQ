
from flask import Blueprint, render_template, request, jsonify
from personalhq.extensions import db, mail
from personalhq.models.waitlist import WaitlistLead
from flask_mail import Message

landing_bp = Blueprint('landing', __name__)

@landing_bp.route('/')
def landing():
    return render_template('landing.html')

@landing_bp.route('/terms')
def terms():
    return render_template('legal/terms.html')

@landing_bp.route('/privacy')
def privacy():
    return render_template('legal/privacy.html')



@landing_bp.route('/api/waitlist', methods=['POST'])
def join_waitlist():
    data = request.get_json()
    email = data.get('email')
    plan = data.get('plan')

    if not email or '@' not in email:
        return jsonify({"status": "error", "message": "Invalid email address"}), 400

    # Prevent duplicates so a user can't spam the button
    existing_lead = WaitlistLead.query.filter_by(email=email.strip().lower(), plan_interest=plan).first()
    
    if not existing_lead:
        new_lead = WaitlistLead(
            email=email.strip().lower(),
            plan_interest=plan
        )
        db.session.add(new_lead)
        db.session.commit()

        # --- OPTIONAL: FLASK-MAIL NOTIFICATION ---
        msg = Message(f"New Waitlist Lead: {plan.title()}",
                      sender="lifehq.support@gmail.com",
                      recipients=["lifehq.support@gmail.com"])
        msg.body = f"A new user joined the waitlist for the {plan.title()} plan!\nEmail: {email}"
        mail.send(msg)

    return jsonify({"status": "success", "message": "You are on the list!"}), 201