"""Application factory for Personal HQ."""

import os
from flask import Flask, render_template
from flask_login import current_user
from personalhq.services.time_service import get_local_now, get_logical_today
from personalhq.extensions import db, bcrypt, login_manager, migrate, csrf, mail
from personalhq import models

from config.development import DevelopmentConfig
from config.production import ProductionConfig
from config.testing import DockerTestingConfig, LocalTestingConfig

CONFIG_MAP = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "docker_testing": DockerTestingConfig,
    "local_testing": LocalTestingConfig
}

def create_app(config_name=None):
    """Creates and configures the Flask application."""
    app = Flask(__name__)

    if config_name is None:
        config_name = os.environ.get("FLASK_CONFIG", "development")

    app.config.from_object(CONFIG_MAP.get(config_name, DevelopmentConfig))

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

    # Global error handlers
    @app.errorhandler(404)
    def not_found(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

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
    from personalhq.routes.identities import identities_api_bp, identities_view_bp
    app.register_blueprint(identities_api_bp)
    app.register_blueprint(identities_view_bp)
    from personalhq.routes.journals import journals_view_bp, journals_api_bp
    app.register_blueprint(journals_view_bp)
    app.register_blueprint(journals_api_bp)
    from personalhq.routes.settings import settings_bp
    app.register_blueprint(settings_bp)


    @app.route('/health')
    def health():
        from flask import jsonify
        return jsonify({"status": "ok"}), 200

    @app.context_processor
    def inject_global_template_variables():
        """Injects variables into ALL templates automatically."""
        if current_user.is_authenticated:
            now = get_local_now()
            logical_today = get_logical_today(current_user)
            is_overtime = now.date() > logical_today
            
            return {
                'is_overtime': is_overtime,
                'today': logical_today # The banner also needs 'today' to show the day name!
            }
            
        # If the user is not logged in (e.g., login page), return safe defaults
        return {
            'is_overtime': False,
            'today': None
        }

    return app