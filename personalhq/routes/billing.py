import stripe
from datetime import datetime, timedelta
from flask import Blueprint, request, redirect, url_for, flash
from flask_login import login_required, current_user
from personalhq.extensions import db
from personalhq.models.plans import Plan
from personalhq.models.users import User
from personalhq.models.subscriptions import Subscription, SubscriptionStatus

billing_bp = Blueprint('billing', __name__, url_prefix='/billing')

@billing_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    # TODO: Replace with your actual Webhook Secret from the Stripe Dashboard on launch day
    endpoint_secret = 'whsec_your_stripe_webhook_secret_here'

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError as e:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        return 'Invalid signature', 400

    # 1. Handle Successful Checkout
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        # This is the current_user.id we passed in the Payment Link URL
        user_id = session.get('client_reference_id') 
        
        if not user_id:
            return 'No user ID found', 400

        # We need to retrieve the session again with line_items expanded 
        # so we can see EXACTLY which price they paid for.
        session_with_items = stripe.checkout.Session.retrieve(
            session['id'], 
            expand=['line_items']
        )
        
        # Get the Stripe Price ID that the user just paid for
        stripe_price_id = session_with_items.line_items.data[0].price.id
        
        # 2. Map Stripe Price IDs to your Database Plan Names
        # TODO: Replace these keys with your actual Price IDs from the Stripe Dashboard
        STRIPE_TO_PLAN_MAP = {
            'price_1Nxy_Pro_Monthly_ID': 'Pro',
            'price_1Nxy_Pro_Annual_ID': 'Pro',
            'price_1Nxy_Limitless_Monthly_ID': 'Limitless',
            'price_1Nxy_Limitless_Annual_ID': 'Limitless',
            'price_1Nxy_Lifetime_ID': 'Lifetime'
        }
        
        plan_name = STRIPE_TO_PLAN_MAP.get(stripe_price_id)
        
        if not plan_name:
            print(f"Unknown Stripe Price ID: {stripe_price_id}")
            return 'Unknown plan', 400

        # 3. Apply the Subscription to the User
        user = User.query.get(user_id)
        plan = Plan.query.filter(Plan.name.ilike(plan_name)).first()

        if user and plan:
            # End any existing active subscriptions to prevent duplicates
            for sub in user.subscriptions.filter_by(status=SubscriptionStatus.ACTIVE):
                sub.status = SubscriptionStatus.CANCELED

            # Calculate end date based on plan (Lifetime = 100 years, others = 31 days buffer)
            # NOTE: For recurring subs, Stripe handles subsequent payments via the 'invoice.payment_succeeded' event.
            if plan_name.lower() == 'lifetime':
                end_date = datetime.now() + timedelta(days=36500)
            else:
                end_date = datetime.now() + timedelta(days=31)

            # Create the new active subscription
            new_sub = Subscription(
                user_id=user.id,
                plan_id=plan.id,
                start_date=datetime.now(),
                end_date=end_date,
                status=SubscriptionStatus.ACTIVE
            )
            
            db.session.add(new_sub)
            db.session.commit()
            print(f"Successfully upgraded User {user_id} to {plan_name}")

    return 'Success', 200

@billing_bp.route('/mock-upgrade/<plan_name>')
@login_required
def mock_upgrade(plan_name):
    """TEMPORARY: Simulates a Stripe payment using your relational schema."""
    
    # 1. Find the Plan in the database (e.g., "Pro" or "Limitless")
    plan = Plan.query.filter(Plan.name.ilike(plan_name)).first()
    
    if not plan:
        flash(f"Plan '{plan_name}' does not exist in the database yet.", "error")
        return redirect(url_for('dashboard.index'))

    # 2. End any existing active subscriptions
    for sub in current_user.subscriptions.filter_by(status=SubscriptionStatus.ACTIVE):
        sub.status = SubscriptionStatus.CANCELED
        
    # 3. Create the new Subscription
    new_sub = Subscription(
        user_id=current_user.id,
        plan_id=plan.id,
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(days=30), # 30 days from now
        status=SubscriptionStatus.ACTIVE
    )
    
    db.session.add(new_sub)
    db.session.commit()
    
    flash(f'Successfully upgraded to {plan.name}!', 'success')
    return redirect(url_for('dashboard.index'))