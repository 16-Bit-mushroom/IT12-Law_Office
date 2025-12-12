# notarial_entry_mdl.py - CORRECTED
from . import db
from datetime import datetime, timezone, timedelta
from sqlalchemy import Numeric
from app.utils.mixins import SoftDeleteMixin

PHT = timezone(timedelta(hours=8))  


class NotarialEntry(db.Model, SoftDeleteMixin):
    __tablename__ = 'notarial_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Notary Book Details
    not_entry_num = db.Column(db.String(255), nullable=False)
    not_page_num = db.Column(db.String(255), nullable=False)
    not_book_num = db.Column(db.String(255), nullable=False)
    not_series = db.Column(db.Integer, nullable=False)
    
    # Document/Instrument title
    not_title = db.Column(db.String(255), nullable=False)
    
    # Date & Time of Notarization
    not_date = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(PHT))
    
    # type of notarial act
    not_type_act = db.Column(db.String(255), nullable=False)
    
    # Fees & O.R No
    not_fee = db.Column(Numeric(10, 2), nullable=False)
    not_fee_or = db.Column(db.String(255), nullable=True)
    
    # Other place of notarization
    not_other_place = db.Column(db.String(255), nullable=True)
    
    # Competent evidence of identity
    not_comp_evidence_id = db.Column(db.String(150), nullable=True)
    
    # Transaction reference
    transaction_item_id = db.Column(db.Integer, db.ForeignKey('transaction_items.id'), nullable=True)
    
    # Transaction status - Store as string, not foreign key
    transaction_status = db.Column(db.String(50), default='no_transaction')  # no_transaction, unpaid, paid
    
    # Relationship with explicit foreign_keys - CORRECTED
    transaction_item = db.relationship('TransactionItem', 
                                     foreign_keys=[transaction_item_id],
                                     backref='notarial_entries',  # Changed from 'notary_entries'
                                     lazy=True)

    def __repr__(self):
        return f"<NotarialEntry(Entry #'{self.not_entry_num}', Title='{self.not_title}', Date='{self.not_date.strftime('%Y-%m-%d')}')>"

    # Properties to check transaction status
    @property
    def has_transaction(self):
        return self.transaction_item_id is not None

    @property
    def is_paid(self):
        return self.transaction_status == 'paid'


class NotarialEntryParty(db.Model):
    __tablename__ = 'notarial_entry_parties'
    
    id = db.Column(db.Integer, primary_key=True)
    notarial_entry_id = db.Column(db.Integer, db.ForeignKey('notarial_entries.id'), nullable=False)
    party_name = db.Column(db.String(150), nullable=False)
    party_address = db.Column(db.String(150), nullable=False)
    
    # ID Details for the party
    party_id_type = db.Column(db.String(50), nullable=True) # e.g., Passport, Drivers License
    party_id_number = db.Column(db.String(50), nullable=True)
    party_id_expiry = db.Column(db.Date, nullable=True)

    notarial_entry = db.relationship('NotarialEntry', backref='parties', lazy=True)


class NotarialEntryWitness(db.Model):
    __tablename__ = 'notarial_entry_witnesses'
    
    id = db.Column(db.Integer, primary_key=True)
    notarial_entry_id = db.Column(db.Integer, db.ForeignKey('notarial_entries.id'), nullable=False)
    witness_name = db.Column(db.String(150), nullable=True)
    witness_address = db.Column(db.String(150), nullable=True)
    
    notarial_entry = db.relationship('NotarialEntry', backref='witnesses', lazy=True)


class NotarialLastEntry(db.Model):
    __tablename__ = 'notarial_last_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Store the last used values
    last_book_num = db.Column(db.String(255), default='1', nullable=False)
    last_page_num = db.Column(db.String(255), default='1', nullable=False)
    last_entry_num = db.Column(db.String(255), default='1', nullable=False)
    
    # To track which user's last entry
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Timestamp
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(PHT), onupdate=lambda: datetime.now(PHT))
    
    # Relationship
    user = db.relationship('User', backref='notarial_last_entry', lazy=True)
    
    def __repr__(self):
        return f"<NotarialLastEntry(book='{self.last_book_num}', page='{self.last_page_num}', entry='{self.last_entry_num}')>"
    
    def increment_entry(self):
        """Increment the entry number, handle page and book overflow"""
        try:
            current_entry = int(self.last_entry_num)
            current_page = int(self.last_page_num)
            current_book = int(self.last_book_num)
            
            # Increment entry
            new_entry = current_entry + 1
            
            # Check if we need to increment page (assuming 50 entries per page)
            if new_entry > 50:
                self.last_entry_num = '1'
                self.last_page_num = str(current_page + 1)
                
                # Check if we need to increment book (assuming 200 pages per book)
                if (current_page + 1) > 200:
                    self.last_page_num = '1'
                    self.last_book_num = str(current_book + 1)
            else:
                self.last_entry_num = str(new_entry)
                
            return {
                'book': self.last_book_num,
                'page': self.last_page_num,
                'entry': self.last_entry_num
            }
        except ValueError:
            # If values aren't integers, just increment entry as string
            self.last_entry_num = str(int(self.last_entry_num) + 1) if self.last_entry_num.isdigit() else '2'
            return {
                'book': self.last_book_num,
                'page': self.last_page_num,
                'entry': self.last_entry_num
            }