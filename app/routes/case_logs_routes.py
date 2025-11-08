from flask import Blueprint, render_template, request, redirect, url_for

case_logs_bp = Blueprint('case_logs', __name__, url_prefix='/case-logs')

@case_logs_bp.route('/')
def case_logs_page():
    # For now, use empty list until we fix the service
    case_logs = []  # get_all_clients() - comment this out temporarily
    return render_template('case_logs_page.html', case_logs=case_logs)
