from flask import Blueprint, render_template, request, redirect, url_for

documents_bp = Blueprint('documents', __name__, url_prefix='/documents')

@documents_bp.route('/')
def documents_page():
    # For now, use empty list until we fix the service
    documents = []  # get_all_clients() - comment this out temporarily
    return render_template('documents_page.html', documents=documents)