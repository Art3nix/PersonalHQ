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
    from personalhq.routes.identities import identities_api_bp, identities_view_bp
    app.register_blueprint(identities_api_bp)
    app.register_blueprint(identities_view_bp)# Inside your create_app() function:
    from personalhq.routes.journals import journals_view_bp, journals_api_bp
    app.register_blueprint(journals_view_bp)
    app.register_blueprint(journals_api_bp)

    # Health check endpoint for monitoring
    @app.route('/health')
    def health():
        """Health check endpoint for load balancers and monitoring."""
        try:
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            return {'status': 'ok', 'database': 'connected'}, 200
        except Exception as e:
            return {'status': 'error', 'error': str(e)}, 500

    # Global error handlers
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors."""
        from flask import render_template
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        from flask import render_template
        db.session.rollback()
        return render_template('errors/500.html'), 500

    return app
