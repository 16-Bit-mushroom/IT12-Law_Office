from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Payment(db.Model):
    """
    Represents a record of a payment transaction.
    """
    __tablename__ = 'payments'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Method of Payment (e.g., 'Cash', 'Credit Card', 'Bank Transfer')
    pay_method = db.Column(db.String(50), nullable=False)
    
    # Reference/Transaction Number (e.g., bank transaction ID, card authorization code)
    # Made unique as this typically identifies a single transaction
    pay_ref = db.Column(db.String(100), unique=True, nullable=False)
    
    # Date and Time of Payment
    pay_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Type of Payment (e.g., 'Invoice Payment', 'Retainer Fee', 'Refund')
    pay_type = db.Column(db.String(50), nullable=False)
    
    # --- Recommended Additional Field (Amount) ---
    # It is highly recommended to include the payment amount
    pay_amount = db.Column(db.Numeric(10, 2), nullable=False) # Use Numeric for precision
    
    # --- Recommended Additional Field (Relationship) ---
    # This payment should likely link to a client, case, or invoice
    # client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    
    # link payments to the items they paid for
    transaction_items = db.relationship('TransactionItem', backref='payment', lazy=True)
    
    def __repr__(self):
        return f"<Payment(id={self.pay_id}, ref='{self.pay_ref}', method='{self.pay_method}')>"