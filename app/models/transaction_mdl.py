from . import db
from datetime import datetime, timezone, timedelta
from sqlalchemy import Numeric

PHT = timezone(timedelta(hours=8))

class TransactionItem(db.Model):
    __tablename__ = 'transaction_items'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False)
    case_id = db.Column(db.Integer, db.ForeignKey('cases.id'), nullable=True)
    
    transaction_type = db.Column(db.String(50), nullable=False)
    purpose = db.Column(db.String(255), nullable=False)
    
    # Total Amount to be paid (The Bill)
    transaction_amount = db.Column(Numeric(10, 2), nullable=False)
    
    # Status: 'Pending', 'Partial', 'Paid'
    payment_status = db.Column(db.String(50), nullable=False, default='Pending')
    
    transaction_date = db.Column(db.DateTime, default=lambda: datetime.now(PHT))
    
    # REMOVED: payment_id (We don't link to just one payment anymore)
    # REMOVED: payment_date (We use the latest payment's date)
    
    # Relationships
    client = db.relationship('Client', backref='transaction_items', lazy=True)
    service = db.relationship('Service', backref='transactions')
    case = db.relationship('Case', backref='transactions', lazy=True)
    
    # Relationship to multiple payments
    payments = db.relationship('Payment', backref='transaction', lazy=True, cascade="all, delete-orphan")

    # --- SMART PROPERTIES ---
    @property
    def total_paid(self):
        """Sum of all linked payments"""
        return sum(p.pay_amount for p in self.payments)

    @property
    def balance(self):
        """Remaining balance"""
        return self.transaction_amount - self.total_paid

    @property
    def is_fully_paid(self):
        return self.balance <= 0