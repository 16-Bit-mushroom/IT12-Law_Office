from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Numeric # Import Numeric for precise money calculations

db = SQLAlchemy()

class Service(db.Model):
    """
    Defines the legal services offered and their standard fees.
    """
    __tablename__ = 'services'
    
    id = db.Column(db.Integer, primary_key=True)
    service_name = db.Column(db.String(100), nullable=False, unique=True) 
    # Use Numeric(precision, scale) for monetary values to prevent floating-point errors.
    fee = db.Column(Numeric(10, 2), nullable=False) 
    description = db.Column(db.Text)
    
    # Relationship to TransactionItem (Many services can be part of many transactions)
    transaction_items = db.relationship('TransactionItem', backref='service', lazy=True)
    
    def __repr__(self):
        return f"<Service(id={self.id}, name='{self.service_name}', fee={self.fee})>"