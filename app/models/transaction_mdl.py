# transaction_mdl.py - OPTIMIZED STRUCTURE
from . import db
from datetime import UTC, datetime
from sqlalchemy import Numeric

class TransactionItem(db.Model):
    __tablename__ = 'transaction_items'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False)
    
    # Optimized status tracking
    transaction_type = db.Column(db.String(50), nullable=False)  # 'Notarial' or 'Case'
    purpose = db.Column(db.String(255), nullable=False)  # Replaces document_title + document_purpose
    
    transaction_amount = db.Column(Numeric(10, 2), nullable=False)
    payment_status = db.Column(db.String(50), nullable=False, default='Pending')  # Pending → Paid
    
    transaction_date = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC))
    payment_date = db.Column(db.DateTime)  # When payment was made
    
    # Foreign key to Payment - KEEP THIS
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id'), nullable=True)
    
    # Relationships - UPDATE THIS
    client = db.relationship('Client', backref='transaction_items', lazy=True)
    service = db.relationship('Service', backref='transactions')
    payment = db.relationship('Payment', backref='transaction_item', foreign_keys=[payment_id])

    def __repr__(self):
        return f"<Transaction(id={self.id}, type='{self.transaction_type}', client='{self.client.full_name}')>"