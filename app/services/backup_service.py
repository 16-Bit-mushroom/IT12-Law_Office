# app/services/backup_service.py
import os
import shutil
import zipfile
import json
import tempfile
from datetime import datetime
from flask import current_app
from sqlalchemy import text
from app import db
from app.models.user_model import User
from app.models.client_mdl import Client
from app.models.service_mdl import Service
from app.models.payment_mdl import Payment
from app.models.transaction_mdl import TransactionItem
from app.models.case_mdl import Case
from app.models.representative_mdl import Representative
from app.models.notarial_entry_mdl import NotarialEntry, NotarialEntryParty, NotarialEntryWitness
from app.models.legal_consultation_mdl import LegalConsultation
from app.models.document_mdl import Document

class BackupService:
    @staticmethod
    def create_full_backup():
        """Create a complete system backup with database + documents"""
        try:
            backup_dir = os.path.join(current_app.instance_path, 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_filename = f"full_system_backup_{timestamp}.zip"
            zip_path = os.path.join(backup_dir, zip_filename)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 1. Add database backup
                database_data = BackupService._create_database_backup()
                zipf.writestr('database.json', json.dumps(database_data, indent=2))
                
                # 2. Add documents
                uploads_root = os.path.join(current_app.root_path, 'uploads')
                if os.path.exists(uploads_root):
                    for root, dirs, files in os.walk(uploads_root):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, current_app.root_path)
                            zipf.write(file_path, arcname)
                
                # 3. Add metadata
                metadata = {
                    'backup_type': 'full_system',
                    'backup_date': datetime.utcnow().isoformat(),
                    'version': '2.1',
                    'file_count': len(zipf.namelist())
                }
                zipf.writestr('metadata.json', json.dumps(metadata, indent=2))
            
            backup_info = {
                'filename': zip_filename,
                'path': zip_path,
                'type': 'full_system',
                'size': os.path.getsize(zip_path),
                'created_at': datetime.utcnow().isoformat()
            }
            BackupService._save_backup_info(backup_info)
            
            current_app.logger.info(f"Full system backup created: {zip_filename}")
            return zip_path
            
        except Exception as e:
            current_app.logger.error(f"Full backup error: {str(e)}")
            raise e

    @staticmethod
    def create_database_backup():
        """Create database-only backup"""
        try:
            backup_data = BackupService._create_database_backup()
            backup_dir = os.path.join(current_app.instance_path, 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"database_backup_{timestamp}.json"
            filepath = os.path.join(backup_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            backup_info = {
                'filename': filename,
                'path': filepath,
                'type': 'database',
                'size': os.path.getsize(filepath),
                'created_at': datetime.utcnow().isoformat()
            }
            BackupService._save_backup_info(backup_info)
            return filepath
        except Exception as e:
            current_app.logger.error(f"Database backup error: {str(e)}")
            raise e

    @staticmethod
    def create_documents_backup():
        """Create documents-only backup"""
        try:
            backup_dir = os.path.join(current_app.instance_path, 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_filename = f"documents_backup_{timestamp}.zip"
            zip_path = os.path.join(backup_dir, zip_filename)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                uploads_root = os.path.join(current_app.root_path, 'uploads')
                if os.path.exists(uploads_root):
                    for root, dirs, files in os.walk(uploads_root):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, current_app.root_path)
                            zipf.write(file_path, arcname)
            
            backup_info = {
                'filename': zip_filename,
                'path': zip_path,
                'type': 'documents',
                'size': os.path.getsize(zip_path),
                'created_at': datetime.utcnow().isoformat()
            }
            BackupService._save_backup_info(backup_info)
            return zip_path
        except Exception as e:
            current_app.logger.error(f"Documents backup error: {str(e)}")
            raise e

    @staticmethod
    def restore_full_system(backup_path):
        """Restore full system from backup ZIP"""
        temp_dir = os.path.join(tempfile.gettempdir(), 'restore_temp')
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)
            
        try:
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(temp_dir)
            
            # 1. Restore database
            database_file = os.path.join(temp_dir, 'database.json')
            if os.path.exists(database_file):
                with open(database_file, 'r') as f:
                    database_data = json.load(f)
                BackupService._restore_database(database_data)
            
            # 2. Restore documents
            target_uploads = os.path.join(current_app.root_path, 'uploads')
            source_new = os.path.join(temp_dir, 'uploads')
            source_old = os.path.join(temp_dir, 'documents')

            if os.path.exists(source_new):
                if not os.path.exists(target_uploads):
                    os.makedirs(target_uploads)
                shutil.copytree(source_new, target_uploads, dirs_exist_ok=True)
            elif os.path.exists(source_old):
                target_docs = os.path.join(target_uploads, 'documents')
                if not os.path.exists(target_docs):
                    os.makedirs(target_docs)
                shutil.copytree(source_old, target_docs, dirs_exist_ok=True)
            
            return True
        except Exception as e:
            current_app.logger.error(f"Full system restore error: {str(e)}")
            raise e
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    @staticmethod
    def restore_database_only(backup_path):
        try:
            with open(backup_path, 'r') as f:
                database_data = json.load(f)
            BackupService._restore_database(database_data)
            return True
        except Exception as e:
            current_app.logger.error(f"Database restore error: {str(e)}")
            raise e

    @staticmethod
    def _restore_database(backup_data):
        try:
            db.session.execute(text('PRAGMA foreign_keys=OFF'))

            # Clear data in dependency order
            tables_to_clear = [
                Document, NotarialEntryWitness, NotarialEntryParty, 
                NotarialEntry, LegalConsultation, Representative,
                Case, TransactionItem, Payment, Service, Client, User
            ]
            
            for model in tables_to_clear:
                try:
                    db.session.query(model).delete()
                except Exception:
                    pass

            db.session.commit()
            
            # Restore order
            models_restore_order = [
                (User, 'users'),
                (Client, 'clients'),
                (Service, 'services'),
                (Payment, 'payments'),
                (TransactionItem, 'transaction_items'),
                (Case, 'cases'),
                (Representative, 'representatives'),
                (NotarialEntry, 'notarial_entries'),
                (NotarialEntryParty, 'notarial_entry_parties'),
                (NotarialEntryWitness, 'notarial_entry_witnesses'),
                (LegalConsultation, 'legal_consultations'),
                (Document, 'documents')
            ]
            
            for model, data_key in models_restore_order:
                if data_key in backup_data and backup_data[data_key]:
                    for record_data in backup_data[data_key]:
                        cleaned_data = {}
                        for key, value in record_data.items():
                            if value is not None and isinstance(value, str):
                                if 'T' in value and ':' in value:
                                    try:
                                        cleaned_data[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                                        continue
                                    except:
                                        pass
                                if '-' in value and ':' in value:
                                    try:
                                        cleaned_data[key] = datetime.fromisoformat(value)
                                        continue
                                    except:
                                        pass
                                if '-' in value and ':' not in value and len(value) == 10:
                                    try:
                                        cleaned_data[key] = datetime.fromisoformat(value).date()
                                        continue
                                    except:
                                        pass
                            cleaned_data[key] = value
                        
                        try:
                            instance = model(**cleaned_data)
                            db.session.add(instance)
                        except Exception as e:
                            current_app.logger.warning(f"Error creating {model.__name__}: {str(e)}")
                            continue
                    
                    db.session.commit()
            
            db.session.execute(text('PRAGMA foreign_keys=ON'))
            return True
            
        except Exception as e:
            db.session.rollback()
            try:
                db.session.execute(text('PRAGMA foreign_keys=ON'))  
            except:
                pass
            raise e

    @staticmethod
    def _create_database_backup():
        backup_data = {
            'metadata': {
                'backup_date': datetime.utcnow().isoformat(),
                'version': '2.1'
            },
            'users': [BackupService.serialize_model(x) for x in User.query.all()],
            'clients': [BackupService.serialize_model(x) for x in Client.query.all()],
            'services': [BackupService.serialize_model(x) for x in Service.query.all()],
            'payments': [BackupService.serialize_model(x) for x in Payment.query.all()],
            'transaction_items': [BackupService.serialize_model(x) for x in TransactionItem.query.all()],
            'cases': [BackupService.serialize_model(x) for x in Case.query.all()],
            'representatives': [BackupService.serialize_model(x) for x in Representative.query.all()],
            'notarial_entries': [BackupService.serialize_model(x) for x in NotarialEntry.query.all()],
            'notarial_entry_parties': [BackupService.serialize_model(x) for x in NotarialEntryParty.query.all()],
            'notarial_entry_witnesses': [BackupService.serialize_model(x) for x in NotarialEntryWitness.query.all()],
            'legal_consultations': [BackupService.serialize_model(x) for x in LegalConsultation.query.all()],
            'documents': [BackupService.serialize_model(x) for x in Document.query.all()]
        }
        return backup_data

    @staticmethod
    def serialize_model(instance):
        if instance is None: return None
        data = {}
        for column in instance.__table__.columns:
            try:
                value = getattr(instance, column.name)
                if value is None: data[column.name] = None
                elif hasattr(value, 'isoformat'): data[column.name] = value.isoformat()
                elif isinstance(value, (int, float, str, bool)): data[column.name] = value
                else: data[column.name] = str(value)
            except: data[column.name] = None
        return data

    @staticmethod
    def get_system_stats():
        try:
            return {
                'users': User.query.count(),
                'clients': Client.query.count(),
                'services': Service.query.count(),
                'payments': Payment.query.count(),
                'transaction_items': TransactionItem.query.count(),
                'cases': Case.query.count(),
                'representatives': Representative.query.count(),
                'notarial_entries': NotarialEntry.query.count(),
                'notarial_entry_parties': NotarialEntryParty.query.count(),
                'notarial_entry_witnesses': NotarialEntryWitness.query.count(),
                'legal_consultations': LegalConsultation.query.count(),
                'documents': Document.query.count(),
            }
        except Exception:
            return {}

    # ... Helper methods (_save_backup_info, get_backup_history, etc.) remain the same ...
    @staticmethod
    def _save_backup_info(backup_info):
        backup_history_file = os.path.join(current_app.instance_path, 'backups', 'backup_history.json')
        history = []
        if os.path.exists(backup_history_file):
            try:
                with open(backup_history_file, 'r') as f:
                    history = json.load(f)
            except:
                pass
        history.append(backup_info)
        history = history[-50:]
        with open(backup_history_file, 'w') as f:
            json.dump(history, f, indent=2)

    @staticmethod
    def get_backup_history():
        backup_history_file = os.path.join(current_app.instance_path, 'backups', 'backup_history.json')
        if not os.path.exists(backup_history_file):
            return []
        try:
            with open(backup_history_file, 'r') as f:
                history = json.load(f)
            return sorted(history, key=lambda x: x['created_at'], reverse=True)
        except:
            return []

    @staticmethod
    def get_system_backup_file(filename):
        return os.path.join(current_app.instance_path, 'backups', filename)

    @staticmethod
    def validate_backup_file(file_path):
        if file_path.endswith('.zip'):
            with zipfile.ZipFile(file_path, 'r') as zipf:
                if 'database.json' in zipf.namelist():
                    return 'full_system'
                return 'documents_only'
        elif file_path.endswith('.json'):
            return 'database'
        raise ValueError("Unsupported format")