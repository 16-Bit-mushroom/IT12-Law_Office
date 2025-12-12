# app/utils/mixins.py
from datetime import datetime, timezone, timedelta
# CHANGE THIS LINE: Import 'db' from 'app.models', NOT 'app'
from app.models import db 

# Define PHT
PHT = timezone(timedelta(hours=8))

class SoftDeleteMixin:
    """
    Adds soft-delete functionality to a model.
    Rows aren't removed; they are just hidden by setting deleted_at.
    """
    deleted_at = db.Column(db.DateTime, nullable=True)

    def soft_delete(self):
        """Mark as deleted"""
        self.deleted_at = datetime.now(PHT)
        db.session.commit()

    def restore(self):
        """Restore from recycle bin"""
        self.deleted_at = None
        db.session.commit()

    @property
    def is_deleted(self):
        return self.deleted_at is not None