# app/services/notarial_entry_service.py
from app.models.notarial_entry_mdl import NotarialEntry, NotarialEntryParty, NotarialEntryWitness
from app.models.transaction_mdl import TransactionItem
from app.models import db
from datetime import datetime, timezone

class NotarialEntryService:
    @staticmethod
    def get_all_entries():
        """Get all notarial entries with their parties and witnesses"""
        return NotarialEntry.query.options(
            db.joinedload(NotarialEntry.parties),
            db.joinedload(NotarialEntry.witnesses)
        ).order_by(NotarialEntry.not_date.desc()).all()

    @staticmethod
    def get_entry_by_id(entry_id):
         """Get a single notarial entry with relationships"""
         return NotarialEntry.query.options(
             db.joinedload(NotarialEntry.parties),
             db.joinedload(NotarialEntry.witnesses)
         ).filter_by(id=entry_id).first()
    
    @staticmethod
    def create_manual_entry(form_data):
        """Create a manual notarial entry with automatic transaction"""
        try:
            # 1. Create the Notarial Entry
            entry = NotarialEntry(
                not_entry_num=form_data['entry_number'],
                not_page_num=form_data['entry_page_num'],
                not_book_num=form_data['entry_book_num'],
                not_series=form_data['not_series'],
                not_title=form_data['document_title'],
                not_date=datetime.strptime(form_data['notarization_date'], '%Y-%m-%dT%H:%M'),
                not_type_act=form_data['notarial_act_type'],
                not_fee=float(form_data['notarial_fee']),
                not_fee_or=form_data.get('notarial_fee_or'),
                not_other_place=form_data.get('other_place'),
                not_comp_evidence_id=form_data.get('not_comp_evidence_id')
            )
            
            db.session.add(entry)
            db.session.flush() # Flush to assign entry.id
            
            # 2. Add Parties
            party_names = form_data.getlist('party_name')
            party_addresses = form_data.getlist('party_address')
            party_id_types = form_data.getlist('party_id_type')
            party_id_numbers = form_data.getlist('party_id_number')
            party_id_expiries = form_data.getlist('party_id_expiry')
            
            for i in range(len(party_names)):
                if party_names[i].strip():
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
                        party_id_type=party_id_types[i] if i < len(party_id_types) else None,
                        party_id_number=party_id_numbers[i] if i < len(party_id_numbers) else None,
                        party_id_expiry=p_expiry
                    )
                    db.session.add(party)

            # 3. Add Witnesses
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

            # 4. Automatically Create TransactionItem
            # IMPORTANT: Ensure Client ID 1 and Service ID 1 exist in your DB, or adjust these defaults.
            transaction = TransactionItem(
            client_id=1,
            service_id=1,
            transaction_type='Notarial',
            purpose=entry.not_title,
            transaction_amount=entry.not_fee,
            payment_status='Pending'  # Will be updated below
            )
            
            db.session.add(transaction)
            db.session.flush()
            
            # 5. Link Transaction to Entry
            if hasattr(entry, 'transaction_item_id'):
                entry.transaction_item_id = transaction.id
            
            # 6. Check if OR number is provided, update both entry and transaction
            or_number = form_data.get('notarial_fee_or', '').strip()
            if or_number:
                entry.transaction_status = 'paid'
                entry.not_fee_or = or_number
                transaction.payment_status = 'Paid'
                transaction.payment_date = datetime.now(timezone.utc)
            else:
                entry.transaction_status = 'unpaid'
                transaction.payment_status = 'Pending'
            
            db.session.commit()
            return entry
            
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def update_entry(entry_id, form_data):
        try:
            entry = NotarialEntry.query.get(entry_id)
            if not entry:   
                return None
            
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
            entry.not_comp_evidence_id = form_data.get('not_comp_evidence_id', '')  # This might be empty
            
            # Update related transaction if fee/title changes
            if hasattr(entry, 'transaction_item') and entry.transaction_item:
                entry.transaction_item.transaction_amount = entry.not_fee
                entry.transaction_item.purpose = entry.not_title
                
            or_number = form_data.get('notarial_fee_or', '')
            if or_number and or_number.strip():
                entry.transaction_status = 'paid'
                if hasattr(entry, 'transaction_item') and entry.transaction_item:
                    entry.transaction_item.payment_status = 'Paid'
                    entry.transaction_item.payment_date = datetime.now(timezone.utc)
            else:
                entry.transaction_status = 'unpaid'
                if hasattr(entry, 'transaction_item') and entry.transaction_item:
                    entry.transaction_item.payment_status = 'Pending'
                    entry.transaction_item.payment_date = None

            # Delete existing parties and witnesses
            NotarialEntryParty.query.filter_by(notarial_entry_id=entry_id).delete()
            NotarialEntryWitness.query.filter_by(notarial_entry_id=entry_id).delete()
            
            # Re-add Parties
            party_names = form_data.getlist('party_name')
            party_addresses = form_data.getlist('party_address')
            party_id_types = form_data.getlist('party_id_type')
            party_id_numbers = form_data.getlist('party_id_number')
            party_id_expiries = form_data.getlist('party_id_expiry')
            
            for i in range(len(party_names)):
                if party_names[i].strip():
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
                        party_id_type=party_id_types[i] if i < len(party_id_types) else None,
                        party_id_number=party_id_numbers[i] if i < len(party_id_numbers) else None,
                        party_id_expiry=p_expiry
                    )
                    db.session.add(party)

            # Re-add Witnesses
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
    def mark_as_paid(entry_id, or_number=None):
        """Mark notarial entry as paid with optional OR number"""
        try:
            entry = NotarialEntry.query.get(entry_id)
            if not entry:
                return None
            
            # Update OR number if provided
            if or_number and or_number.strip():
                entry.not_fee_or = or_number
            
            entry.transaction_status = 'paid'
            
            # Update the actual TransactionItem
            if hasattr(entry, 'transaction_item') and entry.transaction_item:
                entry.transaction_item.payment_status = 'Paid'
                entry.transaction_item.payment_date = datetime.now(timezone.utc)
            
            db.session.commit()
            return entry
            
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def delete_entry(entry_id):
        try:
            entry = NotarialEntry.query.get(entry_id)
            if entry:
                NotarialEntryParty.query.filter_by(notarial_entry_id=entry_id).delete()
                NotarialEntryWitness.query.filter_by(notarial_entry_id=entry_id).delete()
                db.session.delete(entry)
                db.session.commit()
                return True
            return False
        except Exception as e:
            db.session.rollback()
            raise e