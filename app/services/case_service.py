# app/services/case_service.py
from app.models import db
from datetime import datetime, timezone, date, timedelta
from app.models.case_mdl import Case
from app.models.representative_mdl import Representative
from app.models.service_mdl import Service
from app.models.transaction_mdl import TransactionItem
from app.services.suggestion_service import SuggestionService


PHT = timezone(timedelta(hours=8))

class CaseService:
    
    @staticmethod
    def get_all_cases():
        """Get all active cases"""
        # UPDATED: Filter deleted_at
        return Case.query.filter(Case.deleted_at == None).order_by(Case.created_at.desc()).all()
    
    @staticmethod
    def get_case_by_id(case_id):
        """Get a specific case by ID"""
        return Case.query.get(case_id)
    
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
                    if date_val.strip():
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
                filing_date=parse_date(case_data.get('filing_date')),
                client_id=case_data['client_id'],
                assigned_attorney_id=case_data.get('assigned_attorney_id'),
                created_at=datetime.now(PHT),# UPDATED: UTC
                updated_at=datetime.now(PHT)  # UPDATED: UTC
            )
                
            db.session.add(case)
            db.session.flush() 
            
            # 3. Create representatives
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
            
            # 5. Automatically Create TransactionItem
            transaction = TransactionItem(
                client_id=case.client_id,
                service_id=case_service.id,
                case_id=case.id,
                transaction_type='Case',
                purpose=f"Case: {case.title}",
                transaction_amount=0.00,
                payment_status='Pending'
            )
            
            db.session.add(transaction)
            
            # 6. Record suggestions
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
        """Generate unique case number using UTC Year"""
        # UPDATED: Use UTC
        year = datetime.now(PHT).year
        
        last_case = Case.query.filter(
            Case.case_number.like(f'CASE-{year}-%')
        ).order_by(Case.id.desc()).first()
        
        if last_case:
            try:
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
            
            # Handle date conversions safely (FIXED LOGIC)
            if 'engagement_date' in case_data:
                e_date = case_data['engagement_date']
                if isinstance(e_date, str) and e_date.strip():
                    case.engagement_date = datetime.strptime(e_date, '%Y-%m-%d')
                elif isinstance(e_date, (datetime, date)):
                    case.engagement_date = e_date
                
            if 'filing_date' in case_data:
                f_date = case_data['filing_date']
                # Handle empty filing date logic
                if f_date:
                    if isinstance(f_date, str) and f_date.strip():
                        case.filing_date = datetime.strptime(f_date, '%Y-%m-%d')
                    elif isinstance(f_date, (datetime, date)):
                        case.filing_date = f_date
                else:
                    # If it's empty string or None, set to None
                    case.filing_date = None
            
            # Explicitly update timestamp
            case.updated_at = datetime.now(PHT)

            # Update the transaction purpose if exists
            if hasattr(case, 'transactions') and case.transactions:
                for transaction in case.transactions:
                    transaction.purpose = f"Case: {case.title}"
            
            # Update representatives
            if 'representatives' in case_data:
                CaseService._update_representatives(case_id, case_data['representatives'])
            
            # Record suggestions
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
        Representative.query.filter_by(case_id=case_id).delete()
        
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
        """Soft Delete a case"""
        try:
            case = Case.query.get(case_id)
            if not case:
                raise ValueError("Case not found")
            
            case.soft_delete() # Uses Mixin
            return case.case_number
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def get_case_representatives(case_id):
        return Representative.query.filter_by(case_id=case_id).all()