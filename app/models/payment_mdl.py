from . import db
from datetime import datetime
from sqlalchemy import Numeric

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    pay_method = db.Column(db.String(50), nullable=False)
    pay_ref = db.Column(db.String(100), unique=True, nullable=False)
    pay_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    pay_type = db.Column(db.String(50), nullable=False)
    pay_amount = db.Column(Numeric(10, 2), nullable=False)
    
    # Add payment status
    payment_status = db.Column(db.String(50), nullable=False, default='Pending')  # Pending → Paid
    
    # link payments to the items they paid for
    transaction_items = db.relationship('TransactionItem', backref='payment', lazy=True)
    
    def __repr__(self):
        return f"<Payment(id={self.id}, status='{self.payment_status}', amount={self.pay_amount})>"