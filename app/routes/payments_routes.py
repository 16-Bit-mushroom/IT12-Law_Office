from flask import Blueprint, render_template
from flask_login import login_required
from app.models.payment_mdl import Payment

payments_bp = Blueprint('payments', __name__, url_prefix='/payments')

@payments_bp.route('/')
@login_required
def payments_page():
    """Display all payments"""
    payments = Payment.query.all()
    return render_template('payments_page.html', payments=payments)