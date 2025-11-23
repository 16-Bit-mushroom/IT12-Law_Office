from flask import Flask
from app.models import db
from flask_login import LoginManager

def create_app():
    app = Flask(__name__)

    # ================== CONFIGURATION =========================== #
    app.config['SECRET_KEY'] = 'temporary_reset_key_123'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # ================== DATABASE INITIALIZATION =========================== #
    db.init_app(app)

    # ================== AUTHENTICATION (Flask-Login) =========================== #
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'  # Updated to match your auth blueprint
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"

    # Import User model for the user_loader
    from app.models.user_model import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Create database tables
    with app.app_context():
        db.create_all()
        
        from app.services.auth_service import seed_initial_admin
        seed_initial_admin()  # <-- Make sure this is called
    
    # ================== ROUTES =========================== #
    from .routes.clients_routes import clients_bp
    from .routes.dashboard_routes import dashboard_bp
    # from .routes.case_logs_routes import case_logs_bp
    from app.routes.case_routes import case_bp
    from .routes.payments_routes import payments_bp
    from .routes.login_routes import auth_bp
    from .routes.admin_profile_routes import admin_bp
    from .routes.transaction_routes import transaction_bp
    from .routes.notarial_entries_routes import notarial_entries_bp
    from .routes.legal_consultation_routes import legal_consultation_bp
    from .routes.documents_routes import documents_bp
    from .routes.notarial_entries_routes import notarial_entries_bp
    from .routes.settings_route import settings_bp
    

    app.register_blueprint(clients_bp)
    app.register_blueprint(dashboard_bp)
    # app.register_blueprint(case_logs_bp)
    app.register_blueprint(case_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(transaction_bp)
    app.register_blueprint(notarial_entries_bp)
    app.register_blueprint(legal_consultation_bp)
    app.register_blueprint(settings_bp)

    return app