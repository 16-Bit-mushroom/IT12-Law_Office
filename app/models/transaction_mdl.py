from . import db
from datetime import UTC, datetime
from sqlalchemy import Numeric

class TransactionItem(db.Model):
    __tablename__ = 'transaction_items'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False)
    
    # Enhanced status tracking based on your flow
    transaction_status = db.Column(db.String(50), nullable=False, default='Draft')  # Draft → Pending Approval → Approved → Completed
    payment_status = db.Column(db.String(50), nullable=False, default='Pending')   # Pending → Paid
    
    transaction_amount = db.Column(Numeric(10, 2), nullable=False)
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id'), nullable=True)
    
    # Additional fields for workflow
    document_title = db.Column(db.String(255))  # Title of the document being processed
    document_purpose = db.Column(db.Text)       # Purpose/description of the document
    lawyer_notes = db.Column(db.Text)           # Notes from lawyer during approval
    
    transaction_date = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC))
    approved_date = db.Column(db.DateTime)      # When lawyer approved
    completed_date = db.Column(db.DateTime)     # When document was finalized
    
    def __repr__(self):
        return f"<TransactionItem(id={self.id}, status='{self.transaction_status}', client_id={self.client_id})>"