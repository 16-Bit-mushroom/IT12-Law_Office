from flask import Blueprint, render_template, request, redirect, url_for

admin_profile_bp = Blueprint('manage-profile', __name__, url_prefix='/profile')

@admin_profile_bp.route('/')
def admin_profile_page():
    # For now, use empty list until we fix the service
    return render_template('manage_profile_page.html')