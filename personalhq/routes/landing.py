
from flask import Blueprint, render_template

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
