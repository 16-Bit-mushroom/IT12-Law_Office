from . import db  # Import the shared db instance
from datetime import datetime  # Add this import
from sqlalchemy import Numeric


class NotarialEntry(db.Model):
    """
    Represents a single entry in a notarial register (or 'Notary Book').
    """
    __tablename__ = 'notarial_entries'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Notary Book Details
    # number in the notary book
    not_entry_num = db.Column(db.String(255), nullable=False) 

    # page number
    not_page_num = db.Column(db.String(255), nullable=False)

    # book number
    not_book_num = db.Column(db.String(255), nullable=False)

    # series of
    not_series = db.Column(db.String(255), nullable=False)
    
    # Document/Instrument title
    not_title = db.Column(db.String(255), nullable=False) # Increased length for full titles

    # Names & Addresses of parties
    not_party_name = db.Column(db.String(150), nullable=False) 
    not_party_address = db.Column(db.String(150), nullable=False) 
    

    # Names & Addresses of witnesses
    not_witness_name = db.Column(db.String(150), nullable=True)
    not_witness_address = db.Column(db.String(150), nullable=True)

    # competent evidence of identity
    not_comp_evidence_id = db.Column(db.String(150))

    # Date &Time of Notarization
    not_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # type of notarial act
    not_type_act = db.Column(db.String(255), nullable = False)

    # Fees & O.R No
    not_fee = db.Column(Numeric(10, 2), nullable=False)
    not_fee_or = db.Column(db.String(255), nullable=False)
    
    # Other place of notarization other than office of notary public and or remarks
    not_other_place = db.Column(db.String(255), nullable=True)


    # NEW FOREIGN KEY: Links the notary log entry to the specific notarization request
    transaction_item_id = db.Column(db.Integer, db.ForeignKey('transaction_items.id'), nullable=False, unique=True)
    
    # Relationship back to the TransactionItem
    transaction_item = db.relationship('TransactionItem', backref='notary_entry', lazy=True)

    def __repr__(self):
        return f"<NotarialEntry(Entry #'{self.not_entry_num}', Title='{self.not_title}', Date='{self.not_date.strftime('%Y-%m-%d')}')>"