# reminder_service.py - For managing reminders
from app.models import db
from app.models.reminder_mdl import Reminder
from app.models.user_model import User
from datetime import datetime, timedelta
from flask_login import current_user

class ReminderService:
    
    @staticmethod
    def create_reminder(data):
        """
        Create a new reminder
        
        Args:
            data (dict): Reminder data with keys:
                - title (str): Required
                - description (str): Optional
                - remind_at (datetime or str): Required
                - priority (str): 'low', 'medium', 'high', 'urgent'
                - related_case_id (int): Optional
                - related_notarial_id (int): Optional
        
        Returns:
            Reminder: Created reminder
        """
        try:
            # Parse remind_at if it's a string
            remind_at = data.get('remind_at')
            if isinstance(remind_at, str):
                remind_at = datetime.fromisoformat(remind_at.replace('Z', '+00:00'))
            
            reminder = Reminder(
                title=data['title'],
                description=data.get('description', ''),
                remind_at=remind_at,
                priority=data.get('priority', 'medium'),
                status='pending',
                is_recurring=data.get('is_recurring', False),
                recurrence_pattern=data.get('recurrence_pattern'),
                created_by=current_user.id,
                related_case_id=data.get('related_case_id'),
                related_notarial_id=data.get('related_notarial_id'),
                created_at=datetime.utcnow()
            )
            
            db.session.add(reminder)
            db.session.commit()
            return reminder
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def update_reminder(reminder_id, data):
        """
        Update an existing reminder
        
        Args:
            reminder_id (int): Reminder ID
            data (dict): Fields to update
        
        Returns:
            Reminder: Updated reminder
        """
        try:
            reminder = Reminder.query.get(reminder_id)
            if not reminder:
                return None
            
            # Update fields
            if 'title' in data:
                reminder.title = data['title']
            if 'description' in data:
                reminder.description = data['description']
            if 'remind_at' in data:
                remind_at = data['remind_at']
                if isinstance(remind_at, str):
                    remind_at = datetime.fromisoformat(remind_at.replace('Z', '+00:00'))
                reminder.remind_at = remind_at
            if 'priority' in data:
                reminder.priority = data['priority']
            if 'status' in data:
                reminder.status = data['status']
                if data['status'] == 'completed':
                    reminder.completed_at = datetime.utcnow()
            
            reminder.updated_at = datetime.utcnow()
            db.session.commit()
            return reminder
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def delete_reminder(reminder_id):
        """
        Delete a reminder
        
        Args:
            reminder_id (int): Reminder ID
        
        Returns:
            bool: Success status
        """
        try:
            reminder = Reminder.query.get(reminder_id)
            if reminder:
                db.session.delete(reminder)
                db.session.commit()
                return True
            return False
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def get_user_reminders(user_id=None, status='pending', include_overdue=True):
        """
        Get reminders for a user
        
        Args:
            user_id (int): User ID (defaults to current user)
            status (str): 'pending', 'completed', 'cancelled', or 'all'
            include_overdue (bool): Include overdue reminders
        
        Returns:
            list: List of reminders
        """
        if user_id is None and current_user.is_authenticated:
            user_id = current_user.id
        elif user_id is None:
            return []
        
        query = Reminder.query.filter_by(created_by=user_id)
        
        if status != 'all':
            query = query.filter_by(status=status)
        
        if not include_overdue and status == 'pending':
            query = query.filter(Reminder.remind_at >= datetime.utcnow())
        
        return query.order_by(Reminder.remind_at.asc()).all()
    
    @staticmethod
    def get_todays_reminders(user_id=None):
        """
        Get reminders for today
        
        Args:
            user_id (int): User ID (defaults to current user)
        
        Returns:
            list: Today's reminders
        """
        if user_id is None and current_user.is_authenticated:
            user_id = current_user.id
        elif user_id is None:
            return []
        
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        return Reminder.query.filter(
            Reminder.created_by == user_id,
            Reminder.status == 'pending',
            Reminder.remind_at >= today_start,
            Reminder.remind_at < today_end
        ).order_by(Reminder.remind_at.asc()).all()
    
    @staticmethod
    def get_overdue_reminders(user_id=None):
        """
        Get overdue reminders
        
        Args:
            user_id (int): User ID (defaults to current user)
        
        Returns:
            list: Overdue reminders
        """
        if user_id is None and current_user.is_authenticated:
            user_id = current_user.id
        elif user_id is None:
            return []
        
        return Reminder.query.filter(
            Reminder.created_by == user_id,
            Reminder.status == 'pending',
            Reminder.remind_at < datetime.utcnow()
        ).order_by(Reminder.remind_at.asc()).all()
    
    @staticmethod
    def mark_as_completed(reminder_id):
        """
        Mark reminder as completed
        
        Args:
            reminder_id (int): Reminder ID
        
        Returns:
            Reminder: Updated reminder
        """
        return ReminderService.update_reminder(reminder_id, {
            'status': 'completed',
            'completed_at': datetime.utcnow()
        })