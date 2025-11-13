from . import db  # Import the shared db instance


class CaseDocument(db.Model):
    """
    Represents a document associated with a case, tracking its name and completion status.
    """
    __tablename__ = 'case_document'

    # Primary Key
    id = db.Column(db.Integer, primary_key=True)

    # Document Name - Use a variable-length String (String) for flexibility.
    # If you are strictly using a limited set of options (a dropdown), 
    # you might consider a lookup table or an Enum in a more complex setup.
    cas_doc_name = db.Column(db.String, nullable=False) 
    # e.g., 'Initial Complaint', 'Answer to Complaint', 'Discovery Request'

    # Document Status - Use a String for 'lacking' or 'completed'.
    # A fixed-length char or an Enum might be more efficient if the values are strictly limited.
    cas_doc_status = db.Column(db.String, nullable=False) 
    # e.g., 'lacking', 'completed'
    
    # Foreign Key: This is the field that creates the link.
    # It refers to the 'id' column of the 'clients' table.
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    
    # NEW FOREIGN KEY: Links the document to the specific service request that generated it
    transaction_item_id = db.Column(db.Integer, db.ForeignKey('transaction_items.id'), nullable=True)

    # Relationship back to the TransactionItem
    transaction_item = db.relationship('TransactionItem', backref='case_documents', lazy=True)

    def __repr__(self):
        return f"<CaseDocument(id={self.id}, name='{self.cas_doc_name}', status='{self.cas_doc_status}', client_id={self.client_id})>"

# Note: The original use of db.String(120) is perfectly valid if you need 
# to enforce a maximum length of 120 characters for your database schema.