from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

from sqlalchemy import Numeric

db = SQLAlchemy()

class TransactionItem(db.Model):
    """
    Represents a specific service or item requested by a client in a transaction.
    This acts as a line item on an invoice.
    """
    __tablename__ = 'transaction_items'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # --- Foreign Keys ---
    
    # Links to the Client who requested the service
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    
    # Links to the specific Service being requested (e.g., Notarization)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False)
    
    # Links to the Payment that settled this transaction item
    # Nullable=True because a transaction item is often created BEFORE payment is made
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.pay_id'), nullable=True) 
    
    # --- Other Details ---
    
    # Record the price at the time of the transaction (in case the service fee changes later)
    price_at_transaction = db.Column(Numeric(10, 2), nullable=False)
    
    # Status (e.g., 'Pending', 'Paid', 'Cancelled')
    status = db.Column(db.String(50), nullable=False, default='Pending')
    
    # Quantity of this service (e.g., 2 copies of an affidavit)
    quantity = db.Column(db.Integer, nullable=False, default=1) 
    
    # The date the item was requested
    transaction_date = db.Column(db.DateTime, nullable=False, default=datetime.now(datetime.timezone.utc))
    
    
    def __repr__(self):
        return f"<TransactionItem(id={self.id}, client_id={self.client_id}, service_id={self.service_id}, status='{self.status}')>"