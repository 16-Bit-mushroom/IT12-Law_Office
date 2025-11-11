from flask import Blueprint, render_template
from flask_login import login_required

# Assuming your original dashboard blueprint was named 'dashboard'
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/')

@dashboard_bp.route('/')
@login_required # Protects the dashboard
def dashboard_page():
    # The dashboard now requires a logged-in user
    return render_template('dashboard_page.html')

# Assuming you had a separate /dashboard route too
@dashboard_bp.route('/dashboard')
@login_required # Protects the dashboard
def dashboard():
    return render_template('dashboard_page.html')