# services/notarial_entry_service.py - UPDATED
from app.models.notarial_entry_mdl import NotarialEntry, NotarialEntryParty, NotarialEntryWitness
from app.models.transaction_mdl import TransactionItem
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
        ).order_by(NotarialEntry.not_date.desc()).all() # Line 20 or similar

    @staticmethod # Missing staticmethod decorator?
    def get_entry_by_id(entry_id):
         """Get a single notarial entry with relationships"""
         return NotarialEntry.query.options(
             joinedload(NotarialEntry.parties),
             joinedload(NotarialEntry.witnesses)
         ).filter_by(id=entry_id).first()
    
    @staticmethod
    def create_manual_entry(form_data):
        """Create a new manual notarial entry with Party ID details"""
        try:
            # Parse main date
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
                transaction_item_id=None,
                transaction_status='no_transaction'
            )
            
            db.session.add(entry)
            db.session.flush()
            
            # [UPDATED] Add parties with ID details
            party_names = form_data.getlist('party_name')
            party_addresses = form_data.getlist('party_address')
            party_id_types = form_data.getlist('party_id_type')
            party_id_numbers = form_data.getlist('party_id_number')
            party_id_expiries = form_data.getlist('party_id_expiry')
            
            for i in range(len(party_names)):
                if party_names[i].strip():
                    # Handle Date Parsing safely
                    p_expiry = None
                    if i < len(party_id_expiries) and party_id_expiries[i].strip():
                        try:
                            p_expiry = datetime.strptime(party_id_expiries[i], '%Y-%m-%d').date()
                        except ValueError:
                            p_expiry = None

                    party = NotarialEntryParty(
                        notarial_entry_id=entry.id,
                        party_name=party_names[i],
                        party_address=party_addresses[i] if i < len(party_addresses) else '',
                        # Map new fields
                        party_id_type=party_id_types[i] if i < len(party_id_types) else None,
                        party_id_number=party_id_numbers[i] if i < len(party_id_numbers) else None,
                        party_id_expiry=p_expiry
                    )
                    db.session.add(party)
            
            # [Keep Witnesses logic exactly as is]
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
    def update_entry(entry_id, form_data):
        """Update an existing notarial entry with Party ID details"""
        try:
            entry = NotarialEntry.query.get(entry_id)
            if not entry:
                return None
            
            # [Keep existing main entry update logic]
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
            
            # [UPDATED] Add updated parties with IDs
            party_names = form_data.getlist('party_name')
            party_addresses = form_data.getlist('party_address')
            party_id_types = form_data.getlist('party_id_type')
            party_id_numbers = form_data.getlist('party_id_number')
            party_id_expiries = form_data.getlist('party_id_expiry')
            
            for i in range(len(party_names)):
                if party_names[i].strip():
                    # Handle Date Parsing safely
                    p_expiry = None
                    if i < len(party_id_expiries) and party_id_expiries[i].strip():
                        try:
                            p_expiry = datetime.strptime(party_id_expiries[i], '%Y-%m-%d').date()
                        except ValueError:
                            p_expiry = None

                    party = NotarialEntryParty(
                        notarial_entry_id=entry.id,
                        party_name=party_names[i],
                        party_address=party_addresses[i] if i < len(party_addresses) else '',
                        # Map new fields
                        party_id_type=party_id_types[i] if i < len(party_id_types) else None,
                        party_id_number=party_id_numbers[i] if i < len(party_id_numbers) else None,
                        party_id_expiry=p_expiry
                    )
                    db.session.add(party)
            
            # [Keep Witnesses update logic exactly as is]
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

    # NEW: Create transaction for entry
    @staticmethod
    def create_transaction_for_entry(entry_id):
        """Create a transaction for an existing notarial entry"""
        try:
            entry = NotarialEntry.query.get(entry_id)
            if not entry:
                return None
            
            # Create a new transaction item
            transaction = TransactionItem(
                client_id=1,  # Default client - you might want to get this from parties
                service_id=1,  # Default service - you might want to create a "Notarial Service"
                transaction_amount=entry.not_fee,
                document_title=entry.not_title,
                transaction_status='Approved',  # Assuming auto-approval for notarial entries
                payment_status='Pending'
            )
            
            db.session.add(transaction)
            db.session.flush()  # Get the transaction ID
            
            # Link the entry to the transaction
            entry.transaction_item_id = transaction.id
            entry.transaction_status = 'unpaid'
            
            db.session.commit()
            return entry
            
        except Exception as e:
            db.session.rollback()
            raise e

    # NEW: Mark entry as paid
    @staticmethod
    def mark_as_paid(entry_id):
        """Mark notarial entry as paid"""
        try:
            entry = NotarialEntry.query.get(entry_id)
            if not entry:
                return None
            
            entry.transaction_status = 'paid'
            
            # Also update the linked transaction if it exists
            if entry.transaction_item:
                entry.transaction_item.payment_status = 'Paid'
            
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