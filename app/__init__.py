from flask import Flask

def create_app():
    app = Flask(__name__)  # Remove custom template folders
    
    # Import and register blueprints
    from .routes.clients_routes import clients_bp
    app.register_blueprint(clients_bp)

    from .routes.dashboard_routes import dashboard_bp
    app.register_blueprint(dashboard_bp)

    from .routes.case_logs_routes import case_logs_bp
    app.register_blueprint(case_logs_bp)

    from .routes.documents_routes import documents_bp
    app.register_blueprint(documents_bp)
    
    from .routes.payments_routes import payments_bp
    app.register_blueprint(payments_bp)

    from .routes.login_routes import login_bp
    app.register_blueprint(login_bp)

    from .routes.admin_profile_routes import admin_profile_bp
    app.register_blueprint(admin_profile_bp)

    return app