# app/services/notarial_entry_service.py
from app.models.notarial_entry_mdl import NotarialEntry, NotarialEntryParty, NotarialEntryWitness
from app.models.transaction_mdl import TransactionItem
from app.models import db
from datetime import datetime, timezone, timedelta

from app.services.suggestion_service import SuggestionService
from app.models.notarial_entry_mdl import NotarialLastEntry
# from datetime import datetime
from datetime import datetime, timezone, timedelta


PHT = timezone(timedelta(hours=8))


class NotarialEntryService:

    @staticmethod
    def get_notarial_suggestions(field, user_id=None):
        """
        Get suggestions for notarial entry fields
        
        Args:
            field (str): 'title', 'party_id', 'notarial_act', 'book', 'page', 'entry'
            user_id (int): Optional user ID
        
        Returns:
            list: List of suggestion values
        """
        return SuggestionService.get_notarial_suggestions(field, user_id)
    
    @staticmethod
    def get_last_entry_values(user_id=None):
        """
        Get the last used book, page, entry numbers
        
        Args:
            user_id (int): Optional user ID (defaults to global)
        
        Returns:
            dict: {'book': str, 'page': str, 'entry': str}
        """
        if user_id:
            last_entry = NotarialLastEntry.query.filter_by(user_id=user_id).first()
        else:
            last_entry = NotarialLastEntry.query.filter_by(user_id=None).first()
        
        if not last_entry:
            # Create default entry
            last_entry = NotarialLastEntry(
                last_book_num='1',
                last_page_num='1',
                last_entry_num='1',
                user_id=user_id
            )
            db.session.add(last_entry)
            db.session.commit()
        
        return {
            'book': last_entry.last_book_num,
            'page': last_entry.last_page_num,
            'entry': last_entry.last_entry_num
        }
    
    @staticmethod
    def update_last_entry(book_num, page_num, entry_num, user_id=None):
        """
        Update the last used entry values
        
        Args:
            book_num (str): Book number
            page_num (str): Page number
            entry_num (str): Entry number
            user_id (int): Optional user ID
        """
        if user_id:
            last_entry = NotarialLastEntry.query.filter_by(user_id=user_id).first()
        else:
            last_entry = NotarialLastEntry.query.filter_by(user_id=None).first()
        
        if not last_entry:
            last_entry = NotarialLastEntry(
                last_book_num=book_num,
                last_page_num=page_num,
                last_entry_num=entry_num,
                user_id=user_id
            )
            db.session.add(last_entry)
        else:
            last_entry.last_book_num = book_num
            last_entry.last_page_num = page_num
            last_entry.last_entry_num = entry_num
            last_entry.updated_at = datetime.now(PHT) #
        
        db.session.commit()
    
    @staticmethod
    def increment_last_entry(user_id=None):
        """
        Increment the entry number and handle page/book overflow
        
        Args:
            user_id (int): Optional user ID
        
        Returns:
            dict: New values {'book': str, 'page': str, 'entry': str}
        """
        if user_id:
            last_entry = NotarialLastEntry.query.filter_by(user_id=user_id).first()
        else:
            last_entry = NotarialLastEntry.query.filter_by(user_id=None).first()
        
        if not last_entry:
            last_entry = NotarialLastEntry(
                last_book_num='1',
                last_page_num='1',
                last_entry_num='1',
                user_id=user_id
            )
            db.session.add(last_entry)
            db.session.commit()
        
        return last_entry.increment_entry()
    
    @staticmethod
    def record_suggestions_from_entry(entry, user_id):
        """
        Record suggestions from a notarial entry
        
        Args:
            entry (NotarialEntry): The notarial entry
            user_id (int): User ID who created the entry
        """
        try:
            # Record title suggestion
            if entry.not_title:
                SuggestionService.add_suggestion('notarial', 'title', entry.not_title, user_id)
            
            # Record notarial act type
            if entry.not_type_act:
                SuggestionService.add_suggestion('notarial', 'notarial_act', entry.not_type_act, user_id)
            
            # Record book, page, entry numbers
            if entry.not_book_num:
                SuggestionService.add_suggestion('notarial', 'book', entry.not_book_num, user_id)
            
            if entry.not_page_num:
                SuggestionService.add_suggestion('notarial', 'page', entry.not_page_num, user_id)
            
            if entry.not_entry_num:
                SuggestionService.add_suggestion('notarial', 'entry', entry.not_entry_num, user_id)
            
            # Record party ID types from parties
            for party in entry.parties:
                if party.party_id_type:
                    SuggestionService.add_suggestion('notarial', 'party_id', party.party_id_type, user_id)
            
        except Exception as e:
            print(f"Error recording suggestions: {e}")

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
    def create_manual_entry(form_data, user_id):
        """Create a manual notarial entry with automatic transaction - UPDATED"""
        try:
            # 1. Create the Notarial Entry
            entry = NotarialEntry(
                not_entry_num=form_data['entry_number'],
                not_page_num=form_data['entry_page_num'],
                not_book_num=form_data['entry_book_num'],
                not_series=int(form_data['not_series']),
                not_title=form_data['document_title'],
                not_date=datetime.strptime(form_data['notarization_date'], '%Y-%m-%dT%H:%M'),
                not_type_act=form_data['notarial_act_type'],
                not_fee=float(form_data['notarial_fee']),
                not_fee_or=None,
                not_other_place=form_data.get('other_place', ''),
                not_comp_evidence_id=form_data.get('not_comp_evidence_id', '')  # ADDED
            )
            
            db.session.add(entry)
            db.session.flush()
            
            # 2. Add Parties - FIXED with ID fields
            party_names = form_data.getlist('party_name')
            party_addresses = form_data.getlist('party_address')
            party_id_types = form_data.getlist('party_id_type')
            party_id_numbers = form_data.getlist('party_id_number')
            party_id_expiries = form_data.getlist('party_id_expiry')
            
            for i in range(len(party_names)):
                if party_names[i].strip():
                    # Parse ID expiry date if provided
                    p_expiry = None
                    if i < len(party_id_expiries) and party_id_expiries[i].strip():
                        try:
                            p_expiry = datetime.strptime(party_id_expiries[i], '%Y-%m-%d').date()
                        except ValueError:
                            p_expiry = None
                    
                    party = NotarialEntryParty(
                        notarial_entry_id=entry.id,
                        party_name=party_names[i].strip(),
                        party_address=party_addresses[i].strip() if i < len(party_addresses) else '',
                        party_id_type=party_id_types[i].strip() if i < len(party_id_types) and party_id_types[i].strip() else None,
                        party_id_number=party_id_numbers[i].strip() if i < len(party_id_numbers) and party_id_numbers[i].strip() else None,
                        party_id_expiry=p_expiry
                    )
                    db.session.add(party)
            
            # 3. Add Witnesses
            witness_names = form_data.getlist('witness_name')
            witness_addresses = form_data.getlist('witness_address')
            
            for i in range(len(witness_names)):
                if witness_names[i].strip():
                    witness = NotarialEntryWitness(
                        notarial_entry_id=entry.id,
                        witness_name=witness_names[i].strip(),
                        witness_address=witness_addresses[i].strip() if i < len(witness_addresses) else None
                    )
                    db.session.add(witness)
            
            # 4. Record suggestions for auto-complete
            NotarialEntryService.record_suggestions_from_entry(entry, user_id)
            
            # 5. Update last entry values for auto-increment
            NotarialEntryService.update_last_entry(
                entry.not_book_num, 
                entry.not_page_num, 
                entry.not_entry_num, 
                user_id
            )
            
            # 6. Automatically Create TransactionItem
            transaction = TransactionItem(
                client_id=1,  # Default client - should be updated based on your system
                service_id=1,  # Default notarial service
                transaction_type='Notarial',
                purpose=entry.not_title,
                transaction_amount=entry.not_fee,
                payment_status='Pending'
            )
            
            db.session.add(transaction)
            db.session.flush()
            
            # 7. Link Transaction to Entry
            entry.transaction_item_id = transaction.id
            
            # 8. Set entry_reference in transaction
            transaction.entry_reference = f"{entry.not_book_num}-{entry.not_page_num}-{entry.not_entry_num}"
            
           
            
            db.session.commit()
            return entry
            
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def update_entry(entry_id, form_data, user_id):
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
            entry.not_other_place = form_data.get('other_place', '')
            entry.not_comp_evidence_id = form_data.get('not_comp_evidence_id', '')  # This might be empty

            NotarialEntryService.update_last_entry(
            entry.not_book_num, 
            entry.not_page_num, 
            entry.not_entry_num, 
            user_id
        )
        
            # Record suggestions
            NotarialEntryService.record_suggestions_from_entry(entry, user_id)
                
            # Update related transaction if fee/title changes
            if hasattr(entry, 'transaction_item') and entry.transaction_item:
                entry.transaction_item.transaction_amount = entry.not_fee
                entry.transaction_item.purpose = entry.not_title
                

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
                entry.transaction_item.payment_date = datetime.now(PHT)
            
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