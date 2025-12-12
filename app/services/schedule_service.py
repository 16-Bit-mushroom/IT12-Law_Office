# app/services/schedule_service.py
from app import db
from app.models.schedule_mdl import Schedule, ScheduleHistory

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
            # 1. Capture Old State
            old_deadline = schedule.deadline
            new_deadline = data.get('deadline')
            change_reason = data.get('change_reason')

            # 2. Update Basic Fields
            schedule.title = data.get('title')
            schedule.details = data.get('details')
            schedule.priority = data.get('priority')
            schedule.deadline = new_deadline

            # 3. Detect Date Change & Save History
            # Ensure we only create history if the date actually CHANGED
            if old_deadline != new_deadline:
                history = ScheduleHistory(
                    schedule_id=schedule.id,
                    previous_deadline=old_deadline,
                    new_deadline=new_deadline,
                    reason=change_reason or "Date changed" # Fallback text
                )
                db.session.add(history)

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