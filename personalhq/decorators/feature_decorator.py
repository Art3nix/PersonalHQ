"""Decorator for hiding non-MVP features from routes."""

from functools import wraps
from flask import abort, current_app
from personalhq.services.feature_toggle_service import is_enabled, Feature


def require_feature(feature: Feature):
    """
    Decorator to hide routes for disabled features.
    Returns 404 if feature is disabled.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # In MVP, check if feature is enabled
            if not is_enabled(feature):
                # Return 404 to hide the feature
                abort(404)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def hide_feature_in_template(feature: Feature) -> bool:
    """
    Check if a feature should be hidden in templates.
    Usage in Jinja2: {% if not hide_feature_in_template(Feature.JOURNALS) %}
    """
    return not is_enabled(feature)
