from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models.legal_consultation_mdl import LegalConsultation
from app.models.client_mdl import Client
from app.models.transaction_mdl import TransactionItem
from app.models.service_mdl import Service
from app.models import db
from datetime import datetime

legal_consultation_bp = Blueprint('legal_consultation', __name__, url_prefix='/legal-consultation')

@legal_consultation_bp.route('/')
@login_required
def legal_consultation_page():
    """Display all legal consultations"""
    consultations = LegalConsultation.query.order_by(LegalConsultation.consultation_date.desc()).all()
    return render_template('legal_consultation_page.html', consultations=consultations)

@legal_consultation_bp.route('/new', methods=['GET'])
@login_required
def new_consultation_form():
    """Display new consultation form"""
    clients = Client.query.all()
    return render_template('new_consultation.html', clients=clients)

@legal_consultation_bp.route('/new', methods=['POST'])
@login_required
def submit_new_consultation():
    """Create a new legal consultation"""
    try:
        # Get form data
        client_id = request.form['client_id']
        consultation_type = request.form['consultation_type']
        consultation_topic = request.form['consultation_topic']
        consultation_notes = request.form['consultation_notes']
        consultation_duration = request.form['consultation_duration']
        legal_issues = request.form.get('legal_issues', '')
        recommendations = request.form.get('recommendations', '')
        next_steps = request.form.get('next_steps', '')
        follow_up_required = bool(request.form.get('follow_up_required'))
        follow_up_date = request.form.get('follow_up_date')
        
        # Create consultation
        consultation = LegalConsultation(
            client_id=client_id,
            consultation_type=consultation_type,
            consultation_topic=consultation_topic,
            consultation_notes=consultation_notes,
            consultation_duration=consultation_duration,
            legal_issues=legal_issues,
            recommendations=recommendations,
            next_steps=next_steps,
            follow_up_required=follow_up_required,
            follow_up_date=datetime.strptime(follow_up_date, '%Y-%m-%d').date() if follow_up_date else None
        )
        
        db.session.add(consultation)
        db.session.flush()  # Get the consultation ID without committing
        
        # Create transaction record
        legal_service = Service.query.filter_by(service_name='Legal Consultation').first()
        if legal_service:
            transaction = TransactionItem(
                client_id=client_id,
                service_id=legal_service.id,
                transaction_amount=legal_service.fee,
                document_title=f"Legal Consultation: {consultation_topic}",
                document_purpose=consultation_notes,
                transaction_status='Completed'
            )
            db.session.add(transaction)
            db.session.flush()
            
            # Link consultation to transaction
            consultation.transaction_item_id = transaction.id
        
        db.session.commit()
        flash('Legal consultation recorded successfully!', 'success')
        return redirect(url_for('legal_consultation.legal_consultation_page'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error recording consultation: {str(e)}', 'error')
        return redirect(url_for('legal_consultation.new_consultation_form'))