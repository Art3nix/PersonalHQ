"""Business logic for authentication, tokens, and user management."""

from flask import current_app
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from datetime import datetime

from personalhq.extensions import mail, db, bcrypt
from personalhq.models.users import User

def register_new_user(email: str, first_name: str, last_name: str, password: str) -> User | None:
    """Creates a new user if the email is not already registered."""
    if User.query.filter_by(email=email).first():
        return None  # User already exists

    new_user = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        password=password # User model __init__ handles the hashing
    )
    db.session.add(new_user)
    db.session.commit()
    return new_user

def update_last_login(user: User):
    """Updates the last login timestamp for a user."""
    user.last_login = datetime.now()
    db.session.commit()

def generate_reset_token(email: str) -> str:
    """Generate random token for password reset."""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt='password-reset-salt')

def verify_reset_token(token: str, expiration: int = 3600) -> str | None:
    """Verify given token for password reset."""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=expiration)
    except (SignatureExpired, BadSignature):
        return None
    return email

def send_reset_email(to_email: str, reset_url: str):
    """Send email with url to reset the password."""
    msg = Message(
        subject="Personal HQ - Password Reset Request",
        recipients=[to_email],
        body=f"Click the link to reset your password: {reset_url}"
    )
    mail.send(msg)

def update_password(user: User, new_password: str):
    """Updates a user's password securely."""
    user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
    db.session.commit()