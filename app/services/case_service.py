# services/case_service.py
from app.models import db
from datetime import datetime

class CaseService:
    
    @staticmethod
    def get_all_cases():
        """Get all cases ordered by creation date"""
        from app.models.case_mdl import Case
        return Case.query.order_by(Case.created_at.desc()).all()
    
    @staticmethod
    def get_case_by_id(case_id):
        """Get a specific case by ID"""
        from app.models.case_mdl import Case
        return Case.query.get(case_id)
    
    @staticmethod
    def create_case(case_data):
        """Create a new case"""
        from app.models.case_mdl import Case
        
        # Generate case number if not provided
        if not case_data.get('case_number'):
            case_data['case_number'] = CaseService._generate_case_number()
        
        case = Case(
            case_number=case_data['case_number'],
            title=case_data['title'],
            case_category=case_data.get('case_category', 'individual'),
            case_type=case_data.get('case_type', 'general'),
            violation=case_data.get('violation'),
            status=case_data.get('status', 'active'),
            engagement_date=case_data['engagement_date'],
            filing_date=case_data.get('filing_date'),
            client_id=case_data['client_id'],
            assigned_attorney_id=case_data.get('assigned_attorney_id')
        )
        
        db.session.add(case)
        db.session.flush()  # Get the case ID before commit
        
        # Add representatives if provided
        if case_data.get('representatives'):
            CaseService._add_representatives(case.id, case_data['representatives'])
        
        db.session.commit()
        
        return case
    
    @staticmethod
    def _add_representatives(case_id, representatives_data):
        """Add representatives to a case"""
        from app.models.representative_mdl import Representative
        
        for rep_data in representatives_data:
            if rep_data.get('full_name'):  # Only add if name is provided
                representative = Representative(
                    case_id=case_id,
                    full_name=rep_data['full_name'],
                    email=rep_data.get('email'),
                    phone=rep_data.get('phone'),
                    role=rep_data.get('role')
                )
                db.session.add(representative)
    
    @staticmethod
    def _generate_case_number():
        """Generate unique case number"""
        from app.models.case_mdl import Case
        
        year = datetime.now().year
        last_case = Case.query.filter(
            Case.case_number.like(f'CASE-{year}-%')
        ).order_by(Case.id.desc()).first()
        
        if last_case:
            last_number = int(last_case.case_number.split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1
            
        return f"CASE-{year}-{new_number:04d}"

    @staticmethod
    def update_case(case_id, case_data):
        """Update an existing case"""
        from app.models.case_mdl import Case
        
        case = Case.query.get(case_id)
        if not case:
            raise ValueError("Case not found")
        
        # Update fields
        case.title = case_data['title']
        case.case_category = case_data.get('case_category', case.case_category)
        case.case_type = case_data.get('case_type', case.case_type)
        case.violation = case_data.get('violation')
        case.status = case_data.get('status', case.status)
        case.engagement_date = case_data['engagement_date']
        case.filing_date = case_data.get('filing_date')
        case.client_id = case_data['client_id']
        case.assigned_attorney_id = case_data.get('assigned_attorney_id')
        
        # Update representatives if provided
        if 'representatives' in case_data:
            CaseService._update_representatives(case_id, case_data['representatives'])
        
        db.session.commit()
        return case
    
    @staticmethod
    def _update_representatives(case_id, representatives_data):
        """Update representatives for a case"""
        from app.models.representative_mdl import Representative
        
        # Remove existing representatives
        Representative.query.filter_by(case_id=case_id).delete()
        
        # Add new representatives
        if representatives_data:
            CaseService._add_representatives(case_id, representatives_data)
    
    @staticmethod
    def delete_case(case_id):
        """Delete a case"""
        from app.models.case_mdl import Case
        from app.models.representative_mdl import Representative
        
        case = Case.query.get(case_id)
        if not case:
            raise ValueError("Case not found")
        
        # Delete associated representatives
        Representative.query.filter_by(case_id=case_id).delete()
        
        case_number = case.case_number
        db.session.delete(case)
        db.session.commit()
        
        return case_number
    
    @staticmethod
    def get_case_representatives(case_id):
        """Get all representatives for a case"""
        from app.models.representative_mdl import Representative
        return Representative.query.filter_by(case_id=case_id).all()