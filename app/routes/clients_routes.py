from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app  # ADD current_app
from flask_login import login_required
from app.services.client_service import add_client, get_all_clients, get_client_by_email
from app.models.client_mdl import Client
from app import db

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

@clients_bp.route('/new', methods=['POST'])
@login_required 
def submit_new_client():
    """Submits new client data."""
    # Get form data including names
    first_name = request.form['client_first_name']
    last_name = request.form['client_last_name']
    address = request.form['client_address']
    email = request.form['client_email']
    phone = request.form.get('client_phone')
    role = request.form.get('client_role')
    notes = request.form.get('internal_notes', '')

    # Validation: Check for duplicate email
    if get_client_by_email(email):
        flash('A client with this email already exists.', 'error')
        return redirect(url_for('clients.new_client_form'))

    try:
        new_client = add_client(address, email, phone, role, notes, first_name, last_name)
        flash(f'Client {first_name} {last_name} added successfully.', 'success')
        
        # Redirect to case creation with pre-selected client
        return redirect(url_for('case.create_case', pre_select_client_id=new_client.id))
        
    except Exception as e:
        flash(f'An error occurred while adding the client: {e}', 'error')
        # Ensure we keep the return_to parameter if there is an error so they don't lose their place
        return_to = request.args.get('return_to', '')
        return redirect(url_for('clients.new_client_form', return_to=return_to))
    

@clients_bp.route('/api/clients/<int:client_id>')
@login_required
def get_client(client_id):
    """API endpoint to get client details"""
    client = Client.query.get(client_id)
    if client:
        return jsonify({
            'id': client.id,
            'full_name': f"{client.client_first_name} {client.client_last_name}",  # FIXED: use client_first_name and client_last_name
            'email': client.client_email  # FIXED: use client_email
        })
    return jsonify(None)

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