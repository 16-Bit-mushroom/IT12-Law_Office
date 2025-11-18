# services/notarial_entry_service.py - CORRECTED
from app.models.notarial_entry_mdl import NotarialEntry, NotarialEntryParty, NotarialEntryWitness
from app.models import db
from datetime import datetime
from sqlalchemy.orm import joinedload

class NotarialEntryService:
    
    @staticmethod
    def get_all_entries():
        """Get all notarial entries with their parties and witnesses"""
        return NotarialEntry.query.options(
            joinedload(NotarialEntry.parties),
            joinedload(NotarialEntry.witnesses)
        ).order_by(NotarialEntry.not_date.desc()).all()
    
    @staticmethod
    def get_entry_by_id(entry_id):
        """Get a specific notarial entry by ID"""
        return NotarialEntry.query.options(
            joinedload(NotarialEntry.parties),
            joinedload(NotarialEntry.witnesses)
        ).get(entry_id)
    
    @staticmethod
    def create_manual_entry(form_data):
        """Create a new manual notarial entry"""
        try:
            # Parse date
            not_date = datetime.strptime(form_data['notarization_date'], '%Y-%m-%dT%H:%M')
            
            # Create main entry
            entry = NotarialEntry(
                not_entry_num=form_data['entry_number'],
                not_page_num=form_data['entry_page_num'],
                not_book_num=form_data['entry_book_num'],
                not_series=int(form_data['not_series']),
                not_title=form_data['document_title'],
                not_date=not_date,
                not_type_act=form_data['notarial_act_type'],
                not_fee=float(form_data.get('notarial_fee', 0)),
                not_fee_or=form_data.get('notarial_fee_or', ''),
                not_other_place=form_data.get('other_place', ''),
                not_comp_evidence_id=form_data.get('not_comp_evidence_id', ''),
                transaction_item_id=0  # Default for manual entries
            )
            
            db.session.add(entry)
            db.session.flush()  # Get the ID without committing
            
            # Add parties - using correct field names
            party_names = form_data.getlist('party_name')
            party_addresses = form_data.getlist('party_address')
            
            for i in range(len(party_names)):
                if party_names[i].strip():  # Only add if party name exists and is not empty
                    party = NotarialEntryParty(
                        notarial_entry_id=entry.id,
                        party_name=party_names[i],
                        party_address=party_addresses[i] if i < len(party_addresses) else ''
                    )
                    db.session.add(party)
            
            # Add witnesses (0-2)
            witness_names = form_data.getlist('witness_name')
            witness_addresses = form_data.getlist('witness_address')
            
            for i in range(min(len(witness_names), 2)):
                if witness_names[i].strip():  # Only add if witness name exists and is not empty
                    witness = NotarialEntryWitness(
                        notarial_entry_id=entry.id,
                        witness_name=witness_names[i],
                        witness_address=witness_addresses[i] if i < len(witness_addresses) else None
                    )
                    db.session.add(witness)
            
            db.session.commit()
            return entry
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def update_entry(entry_id, form_data):
        """Update an existing notarial entry"""
        try:
            entry = NotarialEntry.query.get(entry_id)
            if not entry:
                return None
            
            # Update main entry
            entry.not_entry_num = form_data['entry_number']
            entry.not_page_num = form_data['entry_page_num']
            entry.not_book_num = form_data['entry_book_num']
            entry.not_series = int(form_data['not_series'])
            entry.not_title = form_data['document_title']
            entry.not_date = datetime.strptime(form_data['notarization_date'], '%Y-%m-%dT%H:%M')
            entry.not_type_act = form_data['notarial_act_type']
            entry.not_fee = float(form_data.get('notarial_fee', 0))
            entry.not_fee_or = form_data.get('notarial_fee_or', '')
            entry.not_other_place = form_data.get('other_place', '')
            entry.not_comp_evidence_id = form_data.get('not_comp_evidence_id', '')
            
            # Clear existing parties and witnesses
            NotarialEntryParty.query.filter_by(notarial_entry_id=entry_id).delete()
            NotarialEntryWitness.query.filter_by(notarial_entry_id=entry_id).delete()
            
            # Add updated parties
            party_names = form_data.getlist('party_name')
            party_addresses = form_data.getlist('party_address')
            
            for i in range(len(party_names)):
                if party_names[i].strip():
                    party = NotarialEntryParty(
                        notarial_entry_id=entry.id,
                        party_name=party_names[i],
                        party_address=party_addresses[i] if i < len(party_addresses) else ''
                    )
                    db.session.add(party)
            
            # Add updated witnesses
            witness_names = form_data.getlist('witness_name')
            witness_addresses = form_data.getlist('witness_address')
            
            for i in range(min(len(witness_names), 2)):
                if witness_names[i].strip():
                    witness = NotarialEntryWitness(
                        notarial_entry_id=entry.id,
                        witness_name=witness_names[i],
                        witness_address=witness_addresses[i] if i < len(witness_addresses) else None
                    )
                    db.session.add(witness)
            
            db.session.commit()
            return entry
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def delete_entry(entry_id):
        """Delete a notarial entry and its related records"""
        try:
            entry = NotarialEntry.query.get(entry_id)
            if entry:
                # Delete related parties and witnesses first
                NotarialEntryParty.query.filter_by(notarial_entry_id=entry_id).delete()
                NotarialEntryWitness.query.filter_by(notarial_entry_id=entry_id).delete()
                db.session.delete(entry)
                db.session.commit()
                return True
            return False
        except Exception as e:
            db.session.rollback()
            raise e