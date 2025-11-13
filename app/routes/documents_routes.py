from flask import Blueprint, render_template
from flask_login import login_required
from app.models.case_doc_mdl import CaseDocument

documents_bp = Blueprint('documents', __name__, url_prefix='/documents')

@documents_bp.route('/')
@login_required
def documents_page():
    """Display all case documents"""
    documents = CaseDocument.query.all()
    return render_template('documents_page.html', documents=documents)