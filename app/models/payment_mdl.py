from . import db
from datetime import datetime
from sqlalchemy import Numeric

# In Payment model - REMOVE the transaction_item_id foreign key
# In TransactionItem model - KEEP payment_id foreign key

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    pay_method = db.Column(db.String(50), nullable=False)
    pay_ref = db.Column(db.String(100), unique=True, nullable=False)
    pay_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    pay_type = db.Column(db.String(50), nullable=False)
    pay_amount = db.Column(Numeric(10, 2), nullable=False)
    payment_status = db.Column(db.String(50), nullable=False, default='Pending')
    
    # NO foreign key to TransactionItem here
    
    def __repr__(self):
        return f"<Payment(id={self.id}, status='{self.payment_status}', amount={self.pay_amount})>"
    def __repr__(self):
        return f"<Payment(id={self.id}, status='{self.payment_status}', amount={self.pay_amount})>"