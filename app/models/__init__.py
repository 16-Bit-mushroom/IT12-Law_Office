from flask_sqlalchemy import SQLAlchemy

# Create a single shared db instance for all models
db = SQLAlchemy()

# Import all models to ensure they are registered with SQLAlchemy
from .user_model import User
from .client_mdl import Client
from .service_mdl import Service
from .payment_mdl import Payment
from .transaction_mdl import TransactionItem
from .case_doc_mdl import CaseDocument
from .notarial_entry_mdl import NotarialEntry
from .legal_consultation_mdl import LegalConsultation