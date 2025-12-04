# suggestion_service.py - For managing auto-suggestions across modules
from app.models import db
from app.models.suggestion_mdl import Suggestion
from datetime import datetime
from flask_login import current_user

class SuggestionService:
    
    @staticmethod
    def get_suggestions(module, suggestion_type, limit=10):
        """
        Get suggestions for a specific module and type
        
        Args:
            module (str): 'notarial', 'case', 'general'
            suggestion_type (str): 'title', 'party_id', 'notarial_act', 'book', 'page', 
                                  'entry', 'case_type', 'violation', 'cause_of_action'
            limit (int): Maximum number of suggestions to return
        
        Returns:
            list: List of suggestion values sorted by frequency
        """
        suggestions = Suggestion.query.filter_by(
            module=module,
            suggestion_type=suggestion_type,
            is_active=True
        ).order_by(
            Suggestion.use_count.desc(),
            Suggestion.last_used.desc()
        ).limit(limit).all()
        
        return [s.value for s in suggestions]
    
    @staticmethod
    def add_suggestion(module, suggestion_type, value, user_id=None):
        """
        Add or update a suggestion
        
        Args:
            module (str): Module name
            suggestion_type (str): Type of suggestion
            value (str): The suggestion value
            user_id (int): Optional user ID who created this
        
        Returns:
            Suggestion: The created/updated suggestion
        """
        if not value or not value.strip():
            return None
            
        value = value.strip()
        
        # Check if suggestion already exists
        suggestion = Suggestion.query.filter_by(
            module=module,
            suggestion_type=suggestion_type,
            value=value
        ).first()
        
        if suggestion:
            # Update existing suggestion
            suggestion.use_count += 1
            suggestion.last_used = datetime.utcnow()
        else:
            # Create new suggestion
            suggestion = Suggestion(
                module=module,
                suggestion_type=suggestion_type,
                value=value,
                use_count=1,
                created_by=user_id or current_user.id if current_user.is_authenticated else None,
                created_at=datetime.utcnow(),
                last_used=datetime.utcnow()
            )
            db.session.add(suggestion)
        
        db.session.commit()
        return suggestion
    
    @staticmethod
    def record_usage(module, suggestion_type, value):
        """
        Record that a suggestion was used (increases use_count)
        
        Args:
            module (str): Module name
            suggestion_type (str): Type of suggestion
            value (str): The suggestion value used
        """
        suggestion = Suggestion.query.filter_by(
            module=module,
            suggestion_type=suggestion_type,
            value=value
        ).first()
        
        if suggestion:
            suggestion.use_count += 1
            suggestion.last_used = datetime.utcnow()
            db.session.commit()
    
    @staticmethod
    def remove_suggestion(module, suggestion_type, value):
        """
        Soft delete a suggestion (set is_active=False)
        
        Args:
            module (str): Module name
            suggestion_type (str): Type of suggestion
            value (str): The suggestion value to remove
        """
        suggestion = Suggestion.query.filter_by(
            module=module,
            suggestion_type=suggestion_type,
            value=value
        ).first()
        
        if suggestion:
            suggestion.is_active = False
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def get_notarial_suggestions(field, limit=10):
        """
        Convenience method for notarial entry suggestions
        
        Args:
            field (str): 'title', 'party_id', 'notarial_act', 'book', 'page', 'entry'
            limit (int): Maximum suggestions
        
        Returns:
            list: Suggestion values
        """
        return SuggestionService.get_suggestions('notarial', field, limit)
    
    @staticmethod
    def get_case_suggestions(field, limit=10):
        """
        Convenience method for case suggestions
        
        Args:
            field (str): 'case_type', 'violation', 'cause_of_action'
            limit (int): Maximum suggestions
        
        Returns:
            list: Suggestion values
        """
        return SuggestionService.get_suggestions('case', field, limit)