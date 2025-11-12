from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

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
    # The original not_party_name_id suggested a foreign key relationship
    # If this model only tracks the name directly, keep it simple:
    not_party_name = db.Column(db.String(150), nullable=False) 
    
    # Foreign Key to a separate 'Client' or 'Person' table 
    # (RECOMMENDED for tracking details like address, ID, etc.)
    # not_party_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=True)
    # party = db.relationship("Client", backref="notarial_entries") # Assuming a 'Client' model exists
    
    # --- Witness Details ---
    
    # Name of the witness to the transaction
    not_witness_name = db.Column(db.String(150))
    # If there are multiple witnesses, you would need a separate 'Witness' table and a many-to-many relationship.
    
    
    # NEW FOREIGN KEY: Links the notary log entry to the specific notarization request
    transaction_item_id = db.Column(db.Integer, db.ForeignKey('transaction_items.id'), nullable=False, unique=True)
    
    # Relationship back to the TransactionItem
    transaction_item = db.relationship('TransactionItem', backref='notary_entry', lazy=True)

    def __repr__(self):
        return f"<NotarialEntry(Entry #'{self.not_entry_num}', Title='{self.not_title}', Date='{self.not_date.strftime('%Y-%m-%d')}')>"