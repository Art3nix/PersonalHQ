"""Module providing API and view routes for authentication."""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from personalhq.forms.auth_forms import LoginForm, RegistrationForm, ForgotPasswordForm, ResetPasswordForm
from personalhq.services import auth_service
from personalhq.models.users import User
from personalhq.extensions import db

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        password = form.password.data
        client_timezone = request.form.get('timezone')

        user = User.query.filter_by(email=email).first()

        # Call the built-in password checker on the model
        if user and user.check_password(password):
            login_user(user, remember=form.remember.data)
            auth_service.update_last_login(user)

            if client_timezone and user.timezone != client_timezone:
                user.timezone = client_timezone
                db.session.commit()
            return redirect(url_for('dashboard.index'))

        flash('Invalid email or password', 'danger')

    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout', methods=['POST', 'GET'])
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = auth_service.register_new_user(
            email=form.email.data.strip().lower(),
            first_name=form.first_name.data.strip(),
            last_name=form.last_name.data.strip(),
            password=form.password.data
        )
        
        if not user:
            flash('Email already registered.', 'danger')
            return render_template('auth/register.html', form=form)

        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    form = ForgotPasswordForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email).first()
        if user:
            token = auth_service.generate_reset_token(email)
            reset_link = url_for('auth.reset_password', token=token, _external=True)
            auth_service.send_reset_email(user.email, reset_link)

        flash('If an account exists with that email, a password reset link has been sent.', 'info')

    return render_template('auth/forgot-password.html', form=form)

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    email = auth_service.verify_reset_token(token)
    if not email:
        flash('Invalid or expired password reset link.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash('Invalid user.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        auth_service.update_password(user, form.password.data)
        flash('Password has been reset. Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset-password.html', form=form, token=token)
from flask import jsonify

@auth_bp.route('/health')
def health():
    return jsonify({"status": "ok"}), 200
