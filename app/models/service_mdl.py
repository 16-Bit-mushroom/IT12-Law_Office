from . import db
from sqlalchemy import Numeric

class Service(db.Model):
    __tablename__ = 'services'

    id = db.Column(db.Integer, primary_key=True)
    service_name = db.Column(db.String(100), nullable=False)
    fee = db.Column(Numeric(10, 2), nullable=False)
    description = db.Column(db.Text)

    def __repr__(self):
        return f"<Service(id={self.id}, name='{self.service_name}', fee={self.fee})>"