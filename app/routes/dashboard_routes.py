from flask import Blueprint, render_template, request, redirect, url_for

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
def dashboard_page():
    # For now, use empty list until we fix the service
    dashboard = []  # get_all_clients() - comment this out temporarily
    return render_template('dashboard_page.html', dashboard=dashboard)