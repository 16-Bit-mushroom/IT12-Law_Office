# notarial_entry_mdl.py - CORRECTED
from . import db
from datetime import datetime
from sqlalchemy import Numeric

class NotarialEntry(db.Model):
    __tablename__ = 'notarial_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Notary Book Details
    not_entry_num = db.Column(db.String(255), nullable=False)
    not_page_num = db.Column(db.String(255), nullable=False)
    not_book_num = db.Column(db.String(255), nullable=False)
    not_series = db.Column(db.Integer, nullable=False)  # Changed to Integer for year only
    
    # Document/Instrument title
    not_title = db.Column(db.String(255), nullable=False)
    
    # Date & Time of Notarization
    not_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # type of notarial act
    not_type_act = db.Column(db.String(255), nullable=False)
    
    # Fees & O.R No
    not_fee = db.Column(Numeric(10, 2), nullable=False)
    not_fee_or = db.Column(db.String(255), nullable=False)
    
    # Other place of notarization
    not_other_place = db.Column(db.String(255), nullable=True)
    
    # Competent evidence of identity
    not_comp_evidence_id = db.Column(db.String(150), nullable=True)
    
    # Foreign Key
    transaction_item_id = db.Column(db.Integer, db.ForeignKey('transaction_items.id'), nullable=False, unique=True)
    transaction_item = db.relationship('TransactionItem', backref='notary_entry', lazy=True)

    def __repr__(self):
        return f"<NotarialEntry(Entry #'{self.not_entry_num}', Title='{self.not_title}', Date='{self.not_date.strftime('%Y-%m-%d')}')>"


class NotarialEntryParty(db.Model):
    __tablename__ = 'notarial_entry_parties'
    
    id = db.Column(db.Integer, primary_key=True)
    notarial_entry_id = db.Column(db.Integer, db.ForeignKey('notarial_entries.id'), nullable=False)
    party_name = db.Column(db.String(150), nullable=False)
    party_address = db.Column(db.String(150), nullable=False)
    
    notarial_entry = db.relationship('NotarialEntry', backref='parties', lazy=True)


class NotarialEntryWitness(db.Model):
    __tablename__ = 'notarial_entry_witnesses'
    
    id = db.Column(db.Integer, primary_key=True)
    notarial_entry_id = db.Column(db.Integer, db.ForeignKey('notarial_entries.id'), nullable=False)
    witness_name = db.Column(db.String(150), nullable=True)
    witness_address = db.Column(db.String(150), nullable=True)
    
    notarial_entry = db.relationship('NotarialEntry', backref='witnesses', lazy=True)