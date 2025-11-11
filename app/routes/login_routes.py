from flask import Blueprint, render_template, request, redirect, url_for

login_bp = Blueprint('login', __name__, url_prefix='/')

@login_bp.route('/')
def login_page():
    # For now, use empty list until we fix the service
    # dashboard = []  # get_all_clients() - comment this out temporarily
    return render_template('login_page.html')