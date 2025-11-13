from . import db  # Import the shared db instance
from datetime import datetime  # Add this import

class NotarialEntry(db.Model):
    """
    Represents a single entry in a notarial register (or 'Notary Book').
    """
    __tablename__ = 'notarial_entries'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Notary Book Details
    # The sequential entry number in the notary book
    not_entry_num = db.Column(db.String(255), nullable=False, unique=True) 
    
    # Document/Instrument title (e.g., 'Special Power of Attorney', 'Deed of Sale')
    not_title = db.Column(db.String(255), nullable=False) # Increased length for full titles
    
    # Date of Notarization
    not_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # --- Party Details (The ones whose documents are being notarized) ---
    
    # Name of the principal party/signer (the one executing the document)
    not_party_name = db.Column(db.String(150), nullable=False) 
    
    # --- Witness Details ---
    
    # Name of the witness to the transaction
    not_witness_name = db.Column(db.String(150))
    
    # NEW FOREIGN KEY: Links the notary log entry to the specific notarization request
    transaction_item_id = db.Column(db.Integer, db.ForeignKey('transaction_items.id'), nullable=False, unique=True)
    
    # Relationship back to the TransactionItem
    transaction_item = db.relationship('TransactionItem', backref='notary_entry', lazy=True)

    def __repr__(self):
        return f"<NotarialEntry(Entry #'{self.not_entry_num}', Title='{self.not_title}', Date='{self.not_date.strftime('%Y-%m-%d')}')>"