from flask import Blueprint, render_template, request, redirect, url_for

payments_bp = Blueprint('payments', __name__, url_prefix='/payments')

@payments_bp.route('/')
def payments_page():
    # For now, use empty list until we fix the service
    payments = []  # get_all_clients() - comment this out temporarily
    return render_template('payments_page.html', payments=payments)