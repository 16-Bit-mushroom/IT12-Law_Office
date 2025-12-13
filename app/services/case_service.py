# app/services/case_service.py
from app.models import db
from datetime import datetime, timezone, date, timedelta
from app.models.case_mdl import Case
from app.models.representative_mdl import Representative
from app.models.service_mdl import Service
from app.models.transaction_mdl import TransactionItem
from app.models.document_mdl import Document
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
        """Create a new case with Logic Validation"""
        try:
            # --- LOGIC RULE 1: NO FILING DATE = PENDING ---
            # If the user tries to set 'Active' but has no filing date, force 'Pending'
            status = case_data.get('status', 'active')
            filing_date = case_data.get('filing_date')
            
            if status == 'active' and not filing_date:
                # Option A: Force it to Pending (User friendly)
                status = 'pending' 
                # Option B: Raise Error (Strict) -> raise ValueError("Active cases must have a filing date.")
            
            # 1. Generate case number
            case_number = CaseService._generate_case_number()
            
            case = Case(
                case_number=case_number,
                title=case_data['title'],
                case_category=case_data.get('case_category', 'individual'),
                case_type=case_data.get('case_type'),
                violation=case_data.get('violation'),
                cause_of_action=case_data.get('cause_of_action'),
                status=status, # Use the validated status
                engagement_date=case_data.get('engagement_date'),
                filing_date=filing_date,
                client_id=case_data['client_id'],
                assigned_attorney_id=case_data.get('assigned_attorney_id'),
                created_at=datetime.now(PHT),
                updated_at=datetime.now(PHT)
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
    def update_case(case_id, case_data, user_role='staff'):
        """Update case with strict Lifecycle Logic"""
        try:
            case = Case.query.get(case_id)
            if not case:
                raise ValueError("Case not found")
            
            # 1. IMMUTABILITY CHECK
            if case.status == 'completed' and user_role != 'admin':
                # Check for content edits (Title, Violation, Client)
                is_editing_content = (
                    case_data.get('title') != case.title or
                    case_data.get('violation') != case.violation or
                    str(case_data.get('client_id')) != str(case.client_id)
                )
                if is_editing_content:
                    raise PermissionError("This case is Closed. Only Admins can edit historical details.")

            # Get new values
            new_status = case_data.get('status', case.status)
            new_filing_date = case_data.get('filing_date') # None or Date object
            
            # --- LOGIC: AUTO-PROMOTE TO ACTIVE ---
            # If currently Pending, and we just added a Filing Date, and user didn't select Complete...
            # Then Auto-switch to Active.
            if case.status == 'pending' and new_filing_date and new_status == 'pending':
                new_status = 'active'
            # -------------------------------------

            # 2. LOGIC RULE: ACTIVE REQUIRES FILING DATE
            if new_status == 'active':
                has_date = new_filing_date or case.filing_date
                if not has_date:
                    raise ValueError("Cannot mark as Active. A Filing Date is required.")

            # 3. LOGIC RULE: COMPLETED REQUIRES NO LACKING DOCS
            if new_status == 'completed':
                lacking_count = Document.query.filter_by(
                    parent_type='case', 
                    parent_id=case.id,
                    document_status='Lacking'
                ).filter(Document.deleted_at == None).count()
                
                if lacking_count > 0:
                    raise ValueError(f"Cannot mark Completed. There are {lacking_count} lacking requirements.")

            # --- SNAPSHOT LOGIC (For History) ---
            if new_status == 'completed' and case.status != 'completed':
                if case.client:
                    # Safely get address
                    addr = getattr(case.client, 'full_address', '')
                    if not addr and hasattr(case.client, 'client_address'): # Fallback for old model
                        addr = case.client.client_address

                    snapshot = {
                        "frozen_at": datetime.now(PHT).strftime('%Y-%m-%d'),
                        "name": case.client.full_name,
                        "email": case.client.email,
                        "phone": case.client.phone,
                        "address": addr,
                        "representative": getattr(case.client, 'designated_representative', None)
                    }
                    case.client_snapshot = json.dumps(snapshot)

            # Apply Updates
            case.title = case_data['title']
            case.case_category = case_data.get('case_category', case.case_category)
            case.case_type = case_data.get('case_type', case.case_type)
            case.violation = case_data.get('violation')
            case.cause_of_action = case_data.get('cause_of_action')
            
            # Handle Dates
            if 'engagement_date' in case_data:
                case.engagement_date = case_data['engagement_date']
            
            if 'filing_date' in case_data:
                case.filing_date = case_data['filing_date']

            case.status = new_status
            case.updated_at = datetime.now(PHT)

            # Update Representatives
            if 'representatives' in case_data:
                CaseService._update_representatives(case_id, case_data['representatives'])
            
            # Record Suggestions
            if case_data.get('case_type'):
                SuggestionService.add_suggestion('case', 'case_type', case_data['case_type'])
            # ...

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