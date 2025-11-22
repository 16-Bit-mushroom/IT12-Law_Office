from . import db

class Client(db.Model):
    __tablename__ = 'clients'

    id = db.Column(db.Integer, primary_key=True)
    client_first_name = db.Column(db.String(100), nullable=False)
    client_last_name = db.Column(db.String(100), nullable=False)
    client_address = db.Column(db.String(255), nullable=False) 
    client_email = db.Column(db.String(120), nullable=False, unique=True)
    client_phone = db.Column(db.String(50))
    client_role = db.Column(db.String(50))
    notes = db.Column(db.Text)

    # Relationships - use backref in Case model instead
    # cases = db.relationship('Case', back_populates='client', lazy=True)
    transaction_items = db.relationship('TransactionItem', backref='client', lazy=True)

    # Property to get full name
    @property
    def full_name(self):
        return f"{self.client_first_name} {self.client_last_name}"

    def __repr__(self):
        return f"<Client(id={self.id}, name='{self.full_name}', email='{self.client_email}')>"