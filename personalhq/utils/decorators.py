from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def requires_access_level(minimum_level):
    """
    Blocks access to a route if the user's plan is not high enough.
    Example: @requires_access_level(2) requires Pro or higher.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
                
            if current_user.access_level < minimum_level:
                flash("This space is reserved for Pro members and above. Consider upgrading to unlock this tool.", "info")
                return redirect(url_for('dashboard.index'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator