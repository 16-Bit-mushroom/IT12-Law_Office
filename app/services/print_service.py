# print_service.py - For generating print templates
from app.models.case_mdl import Case
from app.models.notarial_entry_mdl import NotarialEntry
from app.models.client_mdl import Client
from app.models.user_model import User
from datetime import datetime

class PrintService:
    
    @staticmethod
    def generate_case_print_data(case_id):
        """
        Generate data for case print template
        
        Args:
            case_id (int): Case ID
        
        Returns:
            dict: Formatted case data for printing
        """
        case = Case.query.get(case_id)
        if not case:
            return None
        
        # Format dates
        engagement_date = case.engagement_date.strftime('%B %d, %Y') if case.engagement_date else 'N/A'
        filing_date = case.filing_date.strftime('%B %d, %Y') if case.filing_date else 'N/A'
        created_date = case.created_at.strftime('%B %d, %Y %I:%M %p') if case.created_at else 'N/A'
        
        return {
            'case_number': case.case_number,
            'title': case.title,
            'case_category': case.case_category,
            'case_type': case.case_type,
            'violation': case.violation or 'N/A',
            'cause_of_action': case.cause_of_action or 'N/A',
            'status': case.status,
            'engagement_date': engagement_date,
            'filing_date': filing_date,
            'client_name': case.client.full_name if case.client else 'N/A',
            'client_address': case.client.client_address if case.client else 'N/A',
            'client_email': case.client.client_email if case.client else 'N/A',
            'client_phone': case.client.client_phone if case.client else 'N/A',
            'assigned_attorney': case.assigned_attorney.full_name if case.assigned_attorney else 'N/A',
            'created_at': created_date,
            'print_date': datetime.now().strftime('%B %d, %Y %I:%M %p'),
            'prepared_by': 'System Administrator'  # This should come from current_user in routes
        }
    
    @staticmethod
    def generate_notarial_print_data(entry_id):
        """
        Generate data for notarial entry print template
        
        Args:
            entry_id (int): Notarial entry ID
        
        Returns:
            dict: Formatted notarial data for printing
        """
        entry = NotarialEntry.query.get(entry_id)
        if not entry:
            return None
        
        # Format date and time
        not_date = entry.not_date.strftime('%B %d, %Y %I:%M %p') if entry.not_date else 'N/A'
        
        # Get parties and witnesses
        parties = []
        for party in entry.parties:
            id_expiry = party.party_id_expiry.strftime('%B %d, %Y') if party.party_id_expiry else 'N/A'
            parties.append({
                'name': party.party_name,
                'address': party.party_address,
                'id_type': party.party_id_type or 'N/A',
                'id_number': party.party_id_number or 'N/A',
                'id_expiry': id_expiry
            })
        
        witnesses = []
        for witness in entry.witnesses:
            witnesses.append({
                'name': witness.witness_name or 'N/A',
                'address': witness.witness_address or 'N/A'
            })
        
        return {
            'entry_number': entry.not_entry_num,
            'page_number': entry.not_page_num,
            'book_number': entry.not_book_num,
            'series': entry.not_series,
            'title': entry.not_title,
            'date': not_date,
            'type_of_act': entry.not_type_act,
            'fee': float(entry.not_fee) if entry.not_fee else 0.00,
            'or_number': entry.not_fee_or or 'N/A',
            'other_place': entry.not_other_place or 'N/A',
            'competent_evidence': entry.not_comp_evidence_id or 'N/A',
            'parties': parties,
            'witnesses': witnesses,
            'print_date': datetime.now().strftime('%B %d, %Y %I:%M %p'),
            'prepared_by': 'System Administrator'  # This should come from current_user in routes
        }
    
    @staticmethod
    def get_print_styles():
        """
        Get CSS styles for print templates
        
        Returns:
            str: CSS styles for printing
        """
        return """
            @media print {
                body {
                    font-family: 'Times New Roman', Times, serif;
                    font-size: 12pt;
                    line-height: 1.5;
                    color: #000;
                    margin: 0;
                    padding: 20px;
                }
                
                .no-print {
                    display: none !important;
                }
                
                .print-only {
                    display: block !important;
                }
                
                .print-header {
                    text-align: center;
                    margin-bottom: 30px;
                    border-bottom: 2px solid #000;
                    padding-bottom: 20px;
                }
                
                .print-logo {
                    max-width: 150px;
                    margin: 0 auto 10px;
                }
                
                .print-title {
                    font-size: 16pt;
                    font-weight: bold;
                    margin: 10px 0;
                }
                
                .print-subtitle {
                    font-size: 14pt;
                    margin: 5px 0;
                }
                
                .print-section {
                    margin: 20px 0;
                    page-break-inside: avoid;
                }
                
                .print-section-title {
                    font-size: 13pt;
                    font-weight: bold;
                    border-bottom: 1px solid #000;
                    padding-bottom: 5px;
                    margin-bottom: 10px;
                }
                
                .print-row {
                    display: flex;
                    margin-bottom: 8px;
                }
                
                .print-label {
                    font-weight: bold;
                    width: 200px;
                    min-width: 200px;
                }
                
                .print-value {
                    flex: 1;
                }
                
                .print-table {
                    width: 100%;
                    border-collapse: collapse;
                    margin: 10px 0;
                }
                
                .print-table th {
                    background-color: #f5f5f5;
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                    font-weight: bold;
                }
                
                .print-table td {
                    border: 1px solid #ddd;
                    padding: 8px;
                }
                
                .print-footer {
                    margin-top: 50px;
                    padding-top: 20px;
                    border-top: 1px solid #000;
                    text-align: center;
                    font-size: 10pt;
                }
                
                @page {
                    size: A4;
                    margin: 20mm;
                }
                
                .page-break {
                    page-break-before: always;
                }
            }
            
            .print-container {
                max-width: 210mm;
                margin: 0 auto;
                padding: 20px;
                background: white;
            }
            
            @media screen {
                .print-container {
                    box-shadow: 0 0 10px rgba(0,0,0,0.1);
                }
            }
        """