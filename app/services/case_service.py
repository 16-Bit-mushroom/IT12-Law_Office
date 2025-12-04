# services/case_service.py
from app.models import db
from datetime import datetime
from app.models.case_mdl import Case
from app.models.representative_mdl import Representative
from app.models.service_mdl import Service
from app.models.transaction_mdl import TransactionItem
from app.services.suggestion_service import SuggestionService

class CaseService:
    
    @staticmethod
    def get_all_cases():
        """Get all cases ordered by creation date"""
        return Case.query.order_by(Case.created_at.desc()).all()
    
    @staticmethod
    def get_case_by_id(case_id):
        """Get a specific case by ID"""
        return Case.query.get(case_id)
    
    # Update the create_case method to handle null filing_date
    @staticmethod
    def create_case(case_data):
        """Create a new case with automatic transaction"""
        try:
            # 1. Generate case number
            case_number = CaseService._generate_case_number()
            
            # Helper to handle date parsing safely
            def parse_date(date_val):
                if not date_val:
                    return None
                if isinstance(date_val, str):
                    if date_val.strip():  # Check if not empty string
                        return datetime.strptime(date_val, '%Y-%m-%d')
                    else:
                        return None
                return date_val

            # 2. Create case with cause_of_action
            case = Case(
                case_number=case_number,
                title=case_data['title'],
                case_category=case_data.get('case_category', 'individual'),
                case_type=case_data.get('case_type'),
                violation=case_data.get('violation'),
                cause_of_action=case_data.get('cause_of_action'),
                status=case_data.get('status', 'active'),
                engagement_date=parse_date(case_data.get('engagement_date')),
                filing_date=parse_date(case_data.get('filing_date')),  # This can be None
                client_id=case_data['client_id'],
                assigned_attorney_id=case_data.get('assigned_attorney_id')
            )
                
            db.session.add(case)
            db.session.flush() # Flush to get case.id
            
            # 3. Create representatives if any
            if case_data.get('representatives'):
                for rep_data in case_data['representatives']:
                    if rep_data.get('full_name'):
                        representative = Representative(
                            case_id=case.id,
                            full_name=rep_data['full_name'],
                            email=rep_data.get('email'),
                            phone=rep_data.get('phone'),
                            role=rep_data.get('role')
                        )
                        db.session.add(representative)
            
            # 4. Get or Create Case Service
            case_service = Service.query.filter_by(is_notarization=False).first()
            if not case_service:
                case_service = Service(
                    service_name="Legal Case Service",
                    fee=0.00,
                    is_notarization=False
                )
                db.session.add(case_service)
                db.session.flush()
            
            # 5. Automatically Create TransactionItem WITH case_id
            transaction = TransactionItem(
                client_id=case.client_id,
                service_id=case_service.id,
                case_id=case.id,  # ADD THIS LINE - CRITICAL!
                transaction_type='Case',
                purpose=f"Case: {case.title}",
                transaction_amount=0.00,
                payment_status='Pending'
            )
            
            db.session.add(transaction)
            
            # 6. Record suggestions for auto-complete
            if case_data.get('case_type'):
                SuggestionService.add_suggestion('case', 'case_type', case_data['case_type'])
            if case_data.get('violation'):
                SuggestionService.add_suggestion('case', 'violation', case_data['violation'])
            if case_data.get('cause_of_action'):
                SuggestionService.add_suggestion('case', 'cause_of_action', case_data['cause_of_action'])
            
            db.session.commit()
            return case
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def _generate_case_number():
        """Generate unique case number"""
        year = datetime.now().year
        # Find the last case created this year to increment
        last_case = Case.query.filter(
            Case.case_number.like(f'CASE-{year}-%')
        ).order_by(Case.id.desc()).first()
        
        if last_case:
            try:
                # Extract number from CASE-2024-0001
                last_number = int(last_case.case_number.split('-')[-1])
                new_number = last_number + 1
            except ValueError:
                new_number = 1
        else:
            new_number = 1
            
        return f"CASE-{year}-{new_number:04d}"

    @staticmethod
    def update_case(case_id, case_data):
        """Update an existing case"""
        try:
            case = Case.query.get(case_id)
            if not case:
                raise ValueError("Case not found")
            
            # Update fields
            case.title = case_data['title']
            case.case_category = case_data.get('case_category', case.case_category)
            case.case_type = case_data.get('case_type', case.case_type)
            case.violation = case_data.get('violation')
            case.cause_of_action = case_data.get('cause_of_action')
            case.status = case_data.get('status', case.status)
            
            # Handle date conversions safely
            if 'engagement_date' in case_data:
                e_date = case_data['engagement_date']
                case.engagement_date = datetime.strptime(e_date, '%Y-%m-%d') if isinstance(e_date, str) and e_date.strip() else e_date
                
            if 'filing_date' in case_data:
                f_date = case_data['filing_date']
                # Handle empty filing date
                if f_date and isinstance(f_date, str) and f_date.strip():
                    case.filing_date = datetime.strptime(f_date, '%Y-%m-%d')
                else:
                    case.filing_date = None  # Set to None if empty
            
            # Update the transaction purpose if exists
            if hasattr(case, 'transactions') and case.transactions:
                for transaction in case.transactions:
                    transaction.purpose = f"Case: {case.title}"
            
            # Update representatives if provided
            if 'representatives' in case_data:
                CaseService._update_representatives(case_id, case_data['representatives'])
            
            # Record suggestions for auto-complete
            if case_data.get('case_type'):
                SuggestionService.add_suggestion('case', 'case_type', case_data['case_type'])
            if case_data.get('violation'):
                SuggestionService.add_suggestion('case', 'violation', case_data['violation'])
            if case_data.get('cause_of_action'):
                SuggestionService.add_suggestion('case', 'cause_of_action', case_data['cause_of_action'])
            
            db.session.commit()
            return case
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def _update_representatives(case_id, representatives_data):
        """Update representatives for a case"""
        # Remove existing
        Representative.query.filter_by(case_id=case_id).delete()
        
        # Add new
        if representatives_data:
            for rep_data in representatives_data:
                if rep_data.get('full_name'):
                    representative = Representative(
                        case_id=case_id,
                        full_name=rep_data['full_name'],
                        email=rep_data.get('email'),
                        phone=rep_data.get('phone'),
                        role=rep_data.get('role')
                    )
                    db.session.add(representative)
    
    @staticmethod
    def delete_case(case_id):
        """Delete a case"""
        try:
            case = Case.query.get(case_id)
            if not case:
                raise ValueError("Case not found")
            
            # Delete associated representatives
            Representative.query.filter_by(case_id=case_id).delete()
            
            case_number = case.case_number
            db.session.delete(case)
            db.session.commit()
            
            return case_number
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def get_case_representatives(case_id):
        """Get all representatives for a case"""
        return Representative.query.filter_by(case_id=case_id).all()
    
    @staticmethod
    def get_cases_by_status(status):
        """Get cases filtered by status"""
        if status == 'all':
            return Case.query.order_by(Case.created_at.desc()).all()
        else:
            return Case.query.filter_by(status=status).order_by(Case.created_at.desc()).all()