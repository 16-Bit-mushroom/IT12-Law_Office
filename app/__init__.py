import os
import sys
from flask import Flask
from app.models import db
from flask_login import LoginManager
# from flask_migrate import Migrate

def create_app():
    
    # 1. DEFINE RESOURCE PATH LOGIC (For Templates & Static Files)
    if getattr(sys, 'frozen', False):
        # We are running in a bundle (The .exe)
        template_folder = os.path.join(sys._MEIPASS, 'templates')
        static_folder = os.path.join(sys._MEIPASS, 'static')
        root_path = sys._MEIPASS
    else:
        # We are running in a normal Python environment
        template_folder = 'templates'
        static_folder = 'static'
        root_path = os.getcwd()
        
    app = Flask(__name__, 
                template_folder=template_folder,
                static_folder=static_folder,
                root_path=root_path)

    # ================== DATABASE PATH LOGIC (CRITICAL FOR EXE) =========================== #
    
    if getattr(sys, 'frozen', False):
        # If running as EXE, put the DB in the same folder as the .exe file
        application_path = os.path.dirname(sys.executable)
    else:
        # If running as script, put the DB in the project root
        application_path = os.getcwd()

    db_name = 'app.db'
    db_path = os.path.join(application_path, db_name)
    
    # Fix path separators for Windows to prevent URI errors
    # (SQLite URIs need forward slashes or escaped backslashes)
    if os.name == 'nt':
        db_path = db_path.replace('\\', '\\\\')

    # ================== CONFIGURATION =========================== #
    
    app.config['SECRET_KEY'] = 'temporary_reset_key_123'
    # Use the absolute path we calculated above
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}" 
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    print(f" * Database connected at: {app.config['SQLALCHEMY_DATABASE_URI']}")

    # ================== DATABASE INITIALIZATION =========================== #
    db.init_app(app)

    # ================== AUTHENTICATION (Flask-Login) =========================== #
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"

    # Import User model for the user_loader
    from app.models.user_model import User

    # Context Processor
    @app.context_processor
    def utility_processor():
        def can_access(module):
            from app.utils.permissions import can_access_module
            return can_access_module(module)
        
        def is_admin():
            from flask_login import current_user
            return current_user.is_authenticated and (current_user.is_admin or current_user.role == 'admin')
        
        def is_staff():
            from flask_login import current_user
            return current_user.is_authenticated and current_user.role == 'staff'
        
        return dict(
            can_access=can_access,
            is_admin=is_admin,
            is_staff=is_staff
        )

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Create database tables
    with app.app_context():
        db.create_all()
        
        from app.services.auth_service import seed_initial_admin
        seed_initial_admin()
    
    # ================== ROUTES =========================== #
    from .routes.clients_routes import clients_bp
    from .routes.dashboard_routes import dashboard_bp
    from app.routes.case_routes import case_bp
    from .routes.payments_routes import payments_bp
    from .routes.login_routes import auth_bp
    from .routes.admin_profile_routes import admin_bp
    from .routes.transaction_routes import transaction_bp
    from .routes.notarial_entries_routes import notarial_entries_bp
    from .routes.legal_consultation_routes import legal_consultation_bp
    from .routes.documents_routes import documents_bp
    from .routes.settings_route import settings_bp
    from app.routes.backup_routes import backup_bp
    from .routes.search_routes import search_bp
    from app.routes.recycle_bin_routes import recycle_bp

    app.register_blueprint(clients_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(case_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(transaction_bp)
    app.register_blueprint(notarial_entries_bp)
    app.register_blueprint(legal_consultation_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(backup_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(recycle_bp)

    return app