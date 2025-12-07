from flask_sqlalchemy import SQLAlchemy

# Create a single shared db instance for all models
db = SQLAlchemy()

# Import all models to ensure they are registered with SQLAlchemy
from .user_model import User
from .client_mdl import Client
from .service_mdl import Service
from .payment_mdl import Payment
from .transaction_mdl import TransactionItem
from .case_logs_mdl import CaseDocument
from .case_mdl import Case
from .notarial_entry_mdl import NotarialEntry
from .notarial_entry_mdl import NotarialEntryParty
from .notarial_entry_mdl import NotarialEntryWitness
from .notarial_entry_mdl import NotarialLastEntry  # NEW

from .legal_consultation_mdl import LegalConsultation
from .document_mdl import Document
from .representative_mdl import Representative
from .suggestion_mdl import Suggestion  # NEW
from .reminder_mdl import Reminder  # NEW
from .schedule_mdl import Schedule
from .system_log_mdl import SystemLog