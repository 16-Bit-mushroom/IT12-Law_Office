# app/routes/backup_routes.py
from flask import Blueprint, request, jsonify, send_file, current_app
from flask_login import login_required, current_user
import os
import json
import tempfile # Moved to top level
import shutil   # Moved to top level
from datetime import datetime
from sqlalchemy import text # Required for PRAGMA commands

from app.services.backup_service import BackupService
from app import db 
# UPDATED IMPORTS: Added TransactionItem, Service, Payment. 
# Also using NotarialEntry to match your import list (renamed from NotarialRecord if needed).
from app.models import User, Client, Case, Document, NotarialEntry, LegalConsultation, TransactionItem, Service, Payment

backup_bp = Blueprint('backup', __name__, url_prefix='/backup')

@backup_bp.route('/full', methods=['GET'])
@login_required
def download_full_backup():
    """Download complete system backup"""
    try:
        zip_path = BackupService.create_full_backup()
        filename = os.path.basename(zip_path)
        
        return send_file(
            zip_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/zip'
        )
    except Exception as e:
        current_app.logger.error(f"Full backup download error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@backup_bp.route('/database', methods=['GET'])
@login_required
def download_database_backup():
    """Download database-only backup (advanced)"""
    try:
        filepath = BackupService.create_database_backup()
        filename = os.path.basename(filepath)
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename,
            mimetype='application/json'
        )
    except Exception as e:
        current_app.logger.error(f"Database backup download error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@backup_bp.route('/documents', methods=['GET'])
@login_required
def download_documents_backup():
    """Download documents-only backup (advanced)"""
    try:
        zip_path = BackupService.create_documents_backup()
        filename = os.path.basename(zip_path)
        
        return send_file(
            zip_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/zip'
        )
    except Exception as e:
        current_app.logger.error(f"Documents backup download error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@backup_bp.route('/restore', methods=['POST'])
@login_required
def restore_backup():
    """Restore system from backup file"""
    try:
        restore_source = request.form.get('restore_source')  # 'local' or 'system'
        backup_file_path = None # Initialize variable
        
        # 1. DETERMINE BACKUP SOURCE
        if restore_source == 'local':
            if 'backup_file' not in request.files:
                return jsonify({'error': 'No file provided'}), 400
            
            file = request.files['backup_file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            # Save uploaded file to temporary location
            temp_dir = tempfile.gettempdir()
            backup_file_path = os.path.join(temp_dir, file.filename)
            file.save(backup_file_path)
            
        elif restore_source == 'system':
            backup_filename = request.form.get('backup_filename')
            if not backup_filename:
                return jsonify({'error': 'No backup selected'}), 400
            
            backup_file_path = BackupService.get_system_backup_file(backup_filename)
            if not os.path.exists(backup_file_path):
                return jsonify({'error': 'Backup file not found'}), 404
            
        else:
            return jsonify({'error': 'Invalid restore source'}), 400
        
        # 2. VALIDATE BACKUP FILE
        try:
            backup_type = BackupService.validate_backup_file(backup_file_path)
        except Exception as e:
            # Clean up temp file if validation failed
            if restore_source == 'local' and os.path.exists(backup_file_path):
                os.remove(backup_file_path)
            return jsonify({'error': f'Invalid backup file: {str(e)}'}), 400
        
        # 3. CLEAR DATA AND RESTORE
        try:
            # Disable Foreign Keys
            db.session.execute(text('PRAGMA foreign_keys=OFF'))

            # Clear all tables (Added TransactionItem to fix IntegrityError)
            TransactionItem.query.delete()
            Payment.query.delete() # Assuming Payment exists based on TransactionItem logic
            Document.query.delete()
            LegalConsultation.query.delete()
            NotarialEntry.query.delete() # Changed from NotarialRecord to match your imports
            Case.query.delete()
            Client.query.delete()
            User.query.delete()
            # Service.query.delete() # Uncomment if needed

            db.session.commit()

            # Perform Restore (while FKs are OFF)
            if backup_type == 'full_system':
                success = BackupService.restore_full_system(backup_file_path)
                message = 'Full system restore completed successfully'
            elif backup_type == 'database':
                success = BackupService.restore_database_only(backup_file_path)
                message = 'Database restore completed successfully'
            elif backup_type == 'documents_only':
                # Re-enable FKs before return
                db.session.execute(text('PRAGMA foreign_keys=ON'))
                return jsonify({'error': 'Documents-only restore not yet implemented'}), 501
            else:
                # Re-enable FKs before return
                db.session.execute(text('PRAGMA foreign_keys=ON'))
                return jsonify({'error': 'Unknown backup type'}), 400

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Restore error: {str(e)}")
            return jsonify({'error': f'Restore failed: {str(e)}'}), 500
        
        finally:
            # ALWAYS re-enable Foreign Keys
            try:
                db.session.execute(text('PRAGMA foreign_keys=ON'))
            except Exception as e:
                current_app.logger.error(f"Failed to re-enable FKs: {str(e)}")

        # 4. CLEAN UP
        if restore_source == 'local':
            try:
                if os.path.exists(backup_file_path):
                    os.remove(backup_file_path)
            except:
                pass
        
        if success:
            current_app.logger.info(f"Restore completed: {message}")
            return jsonify({'message': message})
        else:
            return jsonify({'error': 'Restore failed'}), 500
            
    except Exception as e:
        current_app.logger.error(f"Backup restore error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@backup_bp.route('/history', methods=['GET'])
@login_required
def list_backups():
    """Get list of system-stored backups"""
    try:
        # Check if BackupService has get_backup_history, if not fallback to manual listing
        if hasattr(BackupService, 'get_backup_history'):
            backup_files = BackupService.get_backup_history()
            return jsonify({'backups': backup_files})
        else:
             # Fallback logic if method doesn't exist
            return backup_history()
    except Exception as e:
        current_app.logger.error(f"Backup list error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Helper route for history (kept from your original code)
@backup_bp.route('/history_manual') # Renamed to avoid collision if you had duplicates
@login_required
def backup_history():
    """Get list of system backups"""
    try:
        backup_dir = current_app.config.get('BACKUP_DIR', 'backups')
        backups = []
        
        if os.path.exists(backup_dir):
            for filename in os.listdir(backup_dir):
                if filename.endswith(('.zip', '.json')):
                    filepath = os.path.join(backup_dir, filename)
                    stat = os.stat(filepath)
                    
                    if 'full' in filename.lower() or filename.endswith('.zip'):
                        backup_type = 'Full System'
                    elif 'database' in filename.lower() or filename.endswith('.json'):
                        backup_type = 'Database Only'
                    elif 'documents' in filename.lower():
                        backup_type = 'Documents Only'
                    else:
                        backup_type = 'Unknown'
                    
                    backups.append({
                        'filename': filename,
                        'size': stat.st_size,
                        'created_at': stat.st_ctime,
                        'type': backup_type
                    })
        
        backups.sort(key=lambda x: x['created_at'], reverse=True)
        return jsonify({'backups': backups})
        
    except Exception as e:
        current_app.logger.error(f"Error listing backups: {str(e)}")
        return jsonify({'error': str(e)}), 500

@backup_bp.route('/stats', methods=['GET'])
@login_required
def get_system_stats():
    """Get system statistics for backup reporting"""
    try:
        stats = BackupService.get_system_stats()
        return jsonify({'stats': stats})
    except Exception as e:
        current_app.logger.error(f"System stats error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@backup_bp.route('/auto-backup', methods=['POST'])
@login_required
def update_auto_backup():
    """Update auto-backup schedule"""
    try:
        schedule = request.json.get('schedule', 'disabled')
        current_app.logger.info(f"Auto-backup schedule updated to: {schedule}")
        return jsonify({'message': f'Auto-backup schedule set to {schedule}'})
    except Exception as e:
        current_app.logger.error(f"Auto-backup update error: {str(e)}")
        return jsonify({'error': str(e)}), 500