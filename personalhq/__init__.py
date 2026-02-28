"""Application factory for Personal HQ."""

import os
from flask import Flask

# Import the extensions
from personalhq.extensions import db, bcrypt, login_manager, migrate, csrf, mail
from personalhq import models

# Import the configuration classes
from config.development import DevelopmentConfig
from config.production import ProductionConfig
from config.testing import DockerTestingConfig, LocalTestingConfig


# Map environment strings to their respective config objects
CONFIG_MAP = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "docker_testing": DockerTestingConfig,
    "local_testing": LocalTestingConfig
}

def create_app(config_name=None):
    """Creates and configures the Flask application."""
    app = Flask(__name__)

    # Load Configuration
    # Uses the FLASK_CONFIG environment variable defined in docker-compose.yml
    if config_name is None:
        config_name = os.environ.get("FLASK_CONFIG", "development")

    app.config.from_object(CONFIG_MAP.get(config_name, DevelopmentConfig))

    # Initialize Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)


    @login_manager.user_loader
    def load_user(user_id):
        return models.User.query.get(int(user_id))

    #@app.context_processor
    #def inject_logout_form():
    #    return dict(logout_form=LogoutForm())


    # Register Blueprints
    from personalhq.routes.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)
    from personalhq.routes.auth import auth_bp
    app.register_blueprint(auth_bp)
    from personalhq.routes.habits import habits_api_bp, habits_view_bp
    app.register_blueprint(habits_api_bp)
    app.register_blueprint(habits_view_bp)
    from personalhq.routes.braindumps import braindumps_api_bp, braindumps_view_bp
    app.register_blueprint(braindumps_api_bp)
    app.register_blueprint(braindumps_view_bp)
    from personalhq.routes.time_buckets import time_buckets_api_bp, time_buckets_view_bp
    app.register_blueprint(time_buckets_api_bp)
    app.register_blueprint(time_buckets_view_bp)
    from personalhq.routes.focus_sessions import focus_api_bp, focus_view_bp
    app.register_blueprint(focus_api_bp)
    app.register_blueprint(focus_view_bp)

    return app
