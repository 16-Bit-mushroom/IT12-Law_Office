from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Client(db.Model):
    __tablename__ = 'clients'
    
    id = db.Column(db.Integer, primary_key=True)
    client_address = db.Column(db.String(255), nullable=False) # Increased length for addresses
    client_email = db.Column(db.String(120), nullable=False, unique=True) # Added unique constraint
    client_phone = db.Column(db.String(50))
    # It might be better to track client role in a separate table or as a Boolean, 
    # but String(20) works for simple roles like 'Plaintiff', 'Defendant', etc.
    client_role = db.Column(db.String(50)) 
    notes = db.Column(db.Text)
    
    # Relationship to CaseDocument. 'backref' creates a .client attribute on CaseDocument.
    documents = db.relationship('CaseDocument', backref='client', lazy=True)

    # link clients to their transaction items
    transaction_items = db.relationship('TransactionItem', backref='client', lazy=True)
    
    def __repr__(self):
        return f"<Client(id={self.id}, email='{self.client_email}')>"