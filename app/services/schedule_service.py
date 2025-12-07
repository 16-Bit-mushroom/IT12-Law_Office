# app/services/schedule_service.py
from app import db
from app.models.schedule_mdl import Schedule
from datetime import datetime

class ScheduleService:
    @staticmethod
    def create_schedule(data):
        new_schedule = Schedule(
            title=data.get('title'),
            details=data.get('details'),
            deadline=data.get('deadline'),
            priority=data.get('priority', 'normal'),
            case_id=data.get('case_id')
        )
        db.session.add(new_schedule)
        db.session.commit()
        return new_schedule

    @staticmethod
    def get_schedules_by_case(case_id):
        return Schedule.query.filter_by(case_id=case_id).order_by(Schedule.deadline.asc()).all()

    @staticmethod
    def toggle_status(schedule_id):
        schedule = Schedule.query.get(schedule_id)
        if schedule:
            schedule.is_done = not schedule.is_done
            db.session.commit()
            return schedule
    
    @staticmethod
    def get_schedule_by_id(schedule_id):
        return Schedule.query.get(schedule_id)

    @staticmethod
    def update_schedule(schedule_id, data):
        schedule = Schedule.query.get(schedule_id)
        if schedule:
            schedule.title = data.get('title')
            schedule.details = data.get('details')
            schedule.deadline = data.get('deadline')
            schedule.priority = data.get('priority')
            db.session.commit()
            return schedule
        return None

    @staticmethod
    def delete_schedule(schedule_id):
        schedule = Schedule.query.get(schedule_id)
        if schedule:
            db.session.delete(schedule)
            db.session.commit()
            return True
        return False