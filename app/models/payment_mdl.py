from . import db
from datetime import datetime, timezone, timedelta
from sqlalchemy import Numeric

PHT = timezone(timedelta(hours=8))

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Link to the main bill (Transaction)
    transaction_item_id = db.Column(db.Integer, db.ForeignKey('transaction_items.id'), nullable=False)
    
    pay_method = db.Column(db.String(50), nullable=False) # Cash, Check, etc.
    pay_ref = db.Column(db.String(100), nullable=False)   # OR Number / Reference
    pay_date = db.Column(db.DateTime, default=lambda: datetime.now(PHT))
    pay_amount = db.Column(Numeric(10, 2), nullable=False) # Amount paid in this specific installment
    
    notes = db.Column(db.String(255), nullable=True) # Optional remarks

    def __repr__(self):
        return f"<Payment(amount={self.pay_amount}, ref='{self.pay_ref}')>"