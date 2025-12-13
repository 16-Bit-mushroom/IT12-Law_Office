from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app  # ADD current_app
from flask_login import login_required
from app.services.client_service import add_client, get_all_clients, get_client_by_email
from app.models.client_mdl import Client
from app import db
from app.services.system_log_service import SystemLogService

clients_bp = Blueprint('clients', __name__, url_prefix='/clients')

@clients_bp.route('/')
@login_required 
def clients_page():
    # FIX: Only show active clients (not in recycle bin)
    clients = Client.query.filter_by(is_active=True).all()
    return render_template('clients_page.html', clients=clients)

@clients_bp.route('/new', methods=['GET'])
@login_required 
def new_client_form():
    """Displays the form to add a new client."""
    return render_template('add_client.html')


@clients_bp.route('/api/clients/<int:client_id>')
@login_required
def get_client(client_id):
    """API endpoint to get FULL client details for editing"""
    client = Client.query.get(client_id)
    if client:
        return jsonify({
            'id': client.id,
            'client_type': client.client_type,
            'first_name': client.first_name,
            'middle_name': client.middle_name,
            'last_name': client.last_name,
            'company_name': client.company_name,
            'tax_id': client.tax_identification_number,
            'representative': client.designated_representative,
            'email': client.email,
            'phone': client.phone,
            
            # --- FIX: Return Specific Address Parts ---
            'street_address': client.street_address,
            'barangay': client.barangay,
            'city': client.city,
            'province': client.province,
            'zip_code': client.zip_code,
            
            'notes': client.notes
        })
    return jsonify(None)

@clients_bp.route('/new', methods=['POST'])
@login_required 
def submit_new_client():
    """Handles both CREATE and UPDATE for Step 1"""
    data = request.form
    client_id = data.get('client_id') # Hidden Input
    
    try:
        if client_id:
            # === UPDATE MODE ===
            client = Client.query.get(client_id)
            if not client:
                flash('Client not found.', 'error')
                return redirect(url_for('clients.new_client_form'))
            
            # Update fields
            client.client_type = data.get('client_type')
            client.email = data.get('email')
            client.phone = data.get('phone')
            client.street_address = data.get('street_address')
            
            if client.client_type == 'individual':
                client.first_name = data.get('first_name')
                client.middle_name = data.get('middle_name')
                client.last_name = data.get('last_name')
                # Clear corp fields if switching types
                client.company_name = None
            else:
                client.company_name = data.get('company_name')
                client.tax_identification_number = data.get('tax_id')
                client.designated_representative = data.get('representative')
                # Clear indiv fields
                client.first_name = None
                client.last_name = None
            
            db.session.commit()
            SystemLogService.log('Update', 'Client', f"Updated client: {client.full_name}", client.id)
            flash(f'Client details updated.', 'success')
            
        else:
            # === CREATE MODE ===
            # Duplicate Check (Only for Create)
            if get_client_by_email(data.get('email')):
                flash('Email already exists. Please search for the client.', 'error')
                return redirect(url_for('clients.new_client_form'))

            client = Client(
                client_type=data.get('client_type'),
                email=data.get('email'),
                phone=data.get('phone'),
                street_address=data.get('street_address'),
                first_name=data.get('first_name'),
                middle_name=data.get('middle_name'),
                last_name=data.get('last_name'),
                company_name=data.get('company_name'),
                tax_identification_number=data.get('tax_id'),
                designated_representative=data.get('representative')
            )
            db.session.add(client)
            db.session.commit()
            
            SystemLogService.log('Create', 'Client', f"Created new client: {client.full_name}", client.id)
            flash(f'New client created successfully.', 'success')

        # === HANDOFF TO STEP 2 ===
        return redirect(url_for('case.create_case', pre_select_client_id=client.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('clients.new_client_form'))

# REMOVED DUPLICATE list_clients() FUNCTION - KEEP ONLY clients_page()

@clients_bp.route('/<int:client_id>/delete', methods=['POST'])
@login_required
def delete_client(client_id):
    """Soft delete a client - move to recycle bin"""
    try:
        client = Client.query.get_or_404(client_id)
        
        if not client.is_active:
            return jsonify({'error': 'Client is already in recycle bin'}), 400
            
        # Soft delete (move to recycle bin)
        client.soft_delete()
        db.session.commit()
        
        # --- LOGGING ---
        SystemLogService.log('Delete', 'Client', f"Moved client '{client.full_name}' to Recycle Bin", client.id)
        # ---------------
        
        return jsonify({
            'success': True,
            'message': f'Client "{client.full_name}" has been moved to recycle bin.',
            'soft_deleted': True
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting client {client_id}: {str(e)}")  # FIXED: use current_app
        return jsonify({'error': f'Failed to delete client: {str(e)}'}), 500

@clients_bp.route('/recycle-bin')
@login_required
def recycle_bin():
    """View clients in recycle bin"""
    deleted_clients = Client.query.filter_by(is_active=False).order_by(Client.deleted_at.desc()).all()
    return render_template('recycle_bin_clients.html', clients=deleted_clients)

@clients_bp.route('/<int:client_id>/restore', methods=['POST'])
@login_required
def restore_client(client_id):
    """Restore client from recycle bin"""
    try:
        client = Client.query.get_or_404(client_id)
        
        if client.is_active:
            return jsonify({'error': 'Client is not in recycle bin'}), 400
            
        client.restore()
        db.session.commit()
        
        # --- LOGGING ---
        SystemLogService.log('Restore', 'Client', f"Restored client '{client.full_name}' from Recycle Bin", client.id)
        # ---------------
        
        return jsonify({
            'success': True,
            'message': f'Client "{client.full_name}" has been restored from recycle bin.'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error restoring client {client_id}: {str(e)}")  # FIXED: use current_app
        return jsonify({'error': f'Failed to restore client: {str(e)}'}), 500

@clients_bp.route('/<int:client_id>/permanent-delete', methods=['POST'])
@login_required
def permanent_delete_client(client_id):
    """Permanently delete a client from recycle bin"""
    try:
        client = Client.query.get_or_404(client_id)
        
        if client.is_active:
            return jsonify({'error': 'Cannot permanently delete active client. Move to recycle bin first.'}), 400
        
        # Check if client has transactions
        if client.transaction_items:
            return jsonify({
                'error': f'Cannot permanently delete client with {len(client.transaction_items)} transaction(s). Transactions must be preserved for record keeping.'
            }), 400
        
        client_name = client.full_name
        db.session.delete(client)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Client "{client_name}" has been permanently deleted.'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error permanently deleting client {client_id}: {str(e)}")  # FIXED: use current_app
        return jsonify({'error': f'Failed to permanently delete client: {str(e)}'}), 500

@clients_bp.route('/recycle-bin/empty', methods=['POST'])
@login_required
def empty_recycle_bin():
    """Empty recycle bin - permanently delete all clients without transactions"""
    try:
        deleted_clients = Client.query.filter_by(is_active=False).all()
        deleted_count = 0
        preserved_count = 0
        
        for client in deleted_clients:
            if not client.transaction_items:
                db.session.delete(client)
                deleted_count += 1
            else:
                preserved_count += 1
        
        db.session.commit()
        
        message = f'Recycle bin emptied. {deleted_count} client(s) permanently deleted.'
        if preserved_count > 0:
            message += f' {preserved_count} client(s) preserved due to existing transactions.'
        
        return jsonify({
            'success': True,
            'message': message,
            'deleted_count': deleted_count,
            'preserved_count': preserved_count
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error emptying recycle bin: {str(e)}")  # FIXED: use current_app
        return jsonify({'error': f'Failed to empty recycle bin: {str(e)}'}), 500