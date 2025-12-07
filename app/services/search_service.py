# app/services/search_service.py
"""Search Service - Updated to include Party Name search in Documents"""
from app.models import db
from app.models.case_mdl import Case
from app.models.document_mdl import Document
from app.models.notarial_entry_mdl import NotarialEntry, NotarialEntryParty
from app.models.transaction_mdl import TransactionItem
from app.models.client_mdl import Client
from app.models.payment_mdl import Payment
from app.models.representative_mdl import Representative
from sqlalchemy import or_, and_, func
from datetime import datetime
import re


class SearchService:
    
    @staticmethod
    def global_search(query, model_type='all', limit=20):
        """
        Perform global search across all models
        """
        if not query or len(query.strip()) < 2:
            return []
        
        search_term = query.strip().lower()
        results = []
        
        # Search in specified models
        if model_type in ['all', 'cases']:
            results.extend(SearchService._search_cases(search_term, limit))
        
        if model_type in ['all', 'documents']:
            results.extend(SearchService._search_documents(search_term, limit))
        
        if model_type in ['all', 'notarial']:
            results.extend(SearchService._search_notarial_entries(search_term, limit))
        
        if model_type in ['all', 'transactions']:
            results.extend(SearchService._search_transactions(search_term, limit))
        
        if model_type in ['all', 'clients']:
            results.extend(SearchService._search_clients(search_term, limit))
        
        if model_type in ['all', 'payments']:
            results.extend(SearchService._search_payments(search_term, limit))
        
        # Sort by relevance
        for result in results:
            relevance = 0
            title = result.get('title', '').lower()
            description = result.get('description', '').lower()
            
            if search_term in title:
                relevance += 3
            if search_term in description:
                relevance += 1
            
            # Exact matches get highest priority
            if title == search_term:
                relevance += 5
                
            result['relevance'] = relevance
        
        # Sort by relevance and then by date (newest first)
        results.sort(key=lambda x: (x['relevance'], x.get('date_sort', datetime.min)), reverse=True)
        
        return results[:50]
    
    @staticmethod
    def _search_cases(search_term, limit):
        """Search in cases with client names"""
        try:
            conditions = or_(
                Case.title.ilike(f'%{search_term}%'),
                Case.case_number.ilike(f'%{search_term}%'),
                Case.case_type.ilike(f'%{search_term}%'),
                Case.violation.ilike(f'%{search_term}%'),
                Case.status.ilike(f'%{search_term}%'),
                # Search for client names
                Case.client.has(
                    or_(
                        Client.client_first_name.ilike(f'%{search_term}%'),
                        Client.client_last_name.ilike(f'%{search_term}%'),
                        func.concat(Client.client_first_name, ' ', Client.client_last_name).ilike(f'%{search_term}%')
                    )
                ),
                # Search for representatives
                Case.representatives.any(
                    Representative.full_name.ilike(f'%{search_term}%')
                )
            )
            
            cases = Case.query.filter(conditions)\
                .order_by(Case.engagement_date.desc())\
                .limit(limit)\
                .all()
            
            results = []
            for case in cases:
                client_name = case.client.full_name if case.client else "No client"
                
                results.append({
                    'type': 'Case',
                    'subtype': case.case_type or 'Case',
                    'title': f"{case.case_number}: {case.title}",
                    'description': f"Client: {client_name} | Violation: {case.violation or 'N/A'} | Status: {case.status}",
                    'url': f"/cases/{case.id}",
                    'date': case.engagement_date.strftime('%Y-%m-%d'),
                    'date_sort': case.engagement_date,
                    'status': case.status,
                    'relevance': 0
                })
            
            return results
        except Exception as e:
            print(f"Error searching cases: {e}")
            return []
    
    @staticmethod
    def _search_documents(search_term, limit):
        """Search in documents including Parties and Case Clients"""
        try:
            # 1. Find matching Cases (for Case-linked documents)
            matching_case_ids = db.session.query(Case.id).filter(
                or_(
                    Case.case_number.ilike(f'%{search_term}%'),
                    # Also match if the Case's CLIENT name matches
                    Case.client.has(
                        or_(
                            Client.client_first_name.ilike(f'%{search_term}%'),
                            Client.client_last_name.ilike(f'%{search_term}%'),
                            func.concat(Client.client_first_name, ' ', Client.client_last_name).ilike(f'%{search_term}%')
                        )
                    )
                )
            ).all()

            # 2. Find matching Notarial Entries by PARTY NAME (for Notarial-linked documents)
            # This logic finds the IDs of NotarialEntries where a Party matches the search term
            matching_entry_ids = db.session.query(NotarialEntry.id).join(NotarialEntryParty).filter(
                NotarialEntryParty.party_name.ilike(f'%{search_term}%')
            ).all()
            
            # Base conditions (Filename, Type, Notes)
            conditions = or_(
                Document.filename.ilike(f'%{search_term}%'),
                Document.document_type.ilike(f'%{search_term}%'),
                Document.notes.ilike(f'%{search_term}%'),
                Document.document_status.ilike(f'%{search_term}%')
            )
            
            # Add Case linking condition
            if matching_case_ids:
                case_ids_list = [c.id for c in matching_case_ids]
                case_doc_condition = and_(
                    Document.parent_type == 'case',
                    Document.parent_id.in_(case_ids_list)
                )
                conditions = or_(conditions, case_doc_condition)

            # Add Notarial Party linking condition
            if matching_entry_ids:
                entry_ids_list = [e.id for e in matching_entry_ids]
                party_doc_condition = and_(
                    Document.parent_type == 'notarial_entry',
                    Document.parent_id.in_(entry_ids_list)
                )
                conditions = or_(conditions, party_doc_condition)
            
            documents = Document.query.filter(conditions)\
                .order_by(Document.uploaded_at.desc())\
                .limit(limit)\
                .all()
            
            results = []
            for doc in documents:
                context_name = SearchService._get_document_context(doc)
                results.append({
                    'type': 'Document',
                    'subtype': doc.document_type or 'Document',
                    'title': doc.filename,
                    'description': f"Type: {doc.document_type} | Status: {doc.document_status} | {context_name}",
                    'url': f"/documents/download/{doc.id}",
                    'date': doc.uploaded_at.strftime('%Y-%m-%d'),
                    'date_sort': doc.uploaded_at,
                    'status': doc.document_status,
                    'relevance': 0
                })
            
            return results
        except Exception as e:
            print(f"Error searching documents: {e}")
            return []

    @staticmethod
    def _get_document_context(document):
        try:
            if document.parent_type == 'notarial_entry':
                # Try to get the entry details to show party names in context if possible
                entry = NotarialEntry.query.get(document.parent_id)
                if entry:
                    party_names = [p.party_name for p in entry.parties[:2]]
                    party_str = ", ".join(party_names)
                    return f"Notarial: {entry.not_title} ({party_str})"
                return f"Notarial Entry ID: {document.parent_id}"
                
            elif document.parent_type == 'case':
                case = Case.query.get(document.parent_id)
                if case:
                    client_name = case.client.full_name if case.client else "No Client"
                    return f"Case #{case.case_number} ({client_name})"
                return "Unknown Case"
                
            elif document.parent_type == 'client':
                client = Client.query.get(document.parent_id)
                return f"Client: {client.full_name}" if client else "Unknown Client"
            return f"{document.parent_type} #{document.parent_id}"
        except:
            return "Unknown Context"

    @staticmethod
    def _search_notarial_entries(search_term, limit):
        """Search in notarial entries"""
        try:
            # Entry Reference Regex
            entry_ref_match = re.match(r'^(\d+)[\-\s]*(\d+)[\-\s]*(\d+)$', search_term.replace(' ', ''))
            
            base_conditions = or_(
                NotarialEntry.not_title.ilike(f'%{search_term}%'),
                NotarialEntry.not_entry_num.ilike(f'%{search_term}%'),
                NotarialEntry.not_type_act.ilike(f'%{search_term}%'),
                NotarialEntry.not_book_num.ilike(f'%{search_term}%'),
                NotarialEntry.not_page_num.ilike(f'%{search_term}%'),
            )
            
            party_conditions = NotarialEntry.parties.any(
                NotarialEntryParty.party_name.ilike(f'%{search_term}%')
            )
            
            conditions = or_(base_conditions, party_conditions)
            
            if entry_ref_match:
                book_num, page_num, entry_num = entry_ref_match.groups()
                conditions = or_(conditions, and_(
                    NotarialEntry.not_book_num.ilike(f'%{book_num}%'),
                    NotarialEntry.not_page_num.ilike(f'%{page_num}%'),
                    NotarialEntry.not_entry_num.ilike(f'%{entry_num}%')
                ))

            entries = NotarialEntry.query.filter(conditions)\
                .order_by(NotarialEntry.not_date.desc())\
                .limit(limit)\
                .all()
            
            results = []
            for entry in entries:
                party_names = [p.party_name for p in entry.parties[:3]] if entry.parties else []
                entry_ref = f"{entry.not_book_num}-{entry.not_page_num}-{entry.not_entry_num}"
                
                results.append({
                    'type': 'Notarial',
                    'subtype': entry.not_type_act or 'Entry',
                    'title': f"{entry.not_type_act}: {entry.not_title}",
                    'description': f"Entry Ref: {entry_ref} | Parties: {', '.join(party_names)}",
                    'url': f"/notarial-entries/{entry.id}",
                    'date': entry.not_date.strftime('%Y-%m-%d'),
                    'date_sort': entry.not_date,
                    'status': 'N/A',
                    'relevance': 0
                })
            
            return results
        except Exception as e:
            print(f"Error searching notarial: {e}")
            return []

    @staticmethod
    def _search_transactions(search_term, limit):
        """Search in transactions by Purpose, Type, Case Client, and References"""
        try:
            # 1. Basic Text Search on Transaction Fields
            base_conditions = or_(
                TransactionItem.purpose.ilike(f'%{search_term}%'),
                TransactionItem.transaction_type.ilike(f'%{search_term}%'),
                TransactionItem.payment_status.ilike(f'%{search_term}%'),
                TransactionItem.entry_reference.ilike(f'%{search_term}%')
            )
            
            # 2. Direct Client Search (The 'Payer')
            client_conditions = TransactionItem.client.has(
                or_(
                    Client.client_first_name.ilike(f'%{search_term}%'),
                    Client.client_last_name.ilike(f'%{search_term}%'),
                    func.concat(Client.client_first_name, ' ', Client.client_last_name).ilike(f'%{search_term}%')
                )
            )
            
            # 3. Case Client Search (If linked to a case)
            case_client_conditions = TransactionItem.case.has(
                Case.client.has(
                    or_(
                        Client.client_first_name.ilike(f'%{search_term}%'),
                        Client.client_last_name.ilike(f'%{search_term}%'),
                        func.concat(Client.client_first_name, ' ', Client.client_last_name).ilike(f'%{search_term}%')
                    )
                )
            )
            
            # NOTE: TransactionItem does not have a direct 'notarial_entry' relationship in the provided model.
            # Searching "Notarial Parties" directly isn't possible via SQL join here. 
            # However, searching the client name (above) usually covers the primary party.

            conditions = or_(
                base_conditions,
                client_conditions,
                case_client_conditions
            )
            
            transactions = TransactionItem.query.filter(conditions)\
                .order_by(TransactionItem.transaction_date.desc())\
                .limit(limit)\
                .all()
            
            results = []
            for trans in transactions:
                client_name = trans.client.full_name if trans.client else "Unknown Client"
                
                # Build context string
                context_parts = []
                
                if trans.transaction_type == 'Case' and trans.case:
                     # Case Context
                    context_parts.append(f"Case #{trans.case.case_number}")
                    if trans.case.client:
                         context_parts.append(f"Case Client: {trans.case.client.full_name}")
                
                elif trans.transaction_type == 'Notarial':
                    # Notarial Context
                    if trans.entry_reference:
                        context_parts.append(f"Entry Ref: {trans.entry_reference}")
                
                context_str = " | ".join(context_parts)
                
                results.append({
                    'type': 'Transaction',
                    'subtype': trans.transaction_type or 'General',
                    'title': f"{trans.transaction_type}: {trans.purpose}",
                    'description': f"Payer: {client_name} | Amount: ₱{trans.transaction_amount:,.2f} | {context_str}",
                    'url': "/transactions", # Update this if you have a specific detail page
                    'date': trans.transaction_date.strftime('%Y-%m-%d') if trans.transaction_date else 'N/A',
                    'date_sort': trans.transaction_date or datetime.min,
                    'status': trans.payment_status,
                    'relevance': 0
                })
            
            return results
        except Exception as e:
            print(f"Error searching transactions: {e}")
            return []

    @staticmethod
    def _search_clients(search_term, limit):
        """Search in clients"""
        try:
            conditions = or_(
                Client.client_first_name.ilike(f'%{search_term}%'),
                Client.client_last_name.ilike(f'%{search_term}%'),
                Client.client_email.ilike(f'%{search_term}%'),
                func.concat(Client.client_first_name, ' ', Client.client_last_name).ilike(f'%{search_term}%')
            )
            
            clients = Client.query.filter(and_(conditions, Client.is_active == True))\
                .order_by(Client.id.desc())\
                .limit(limit)\
                .all()
            
            results = []
            for client in clients:
                results.append({
                    'type': 'Client',
                    'subtype': client.client_role or 'Client',
                    'title': client.full_name,
                    'description': f"Email: {client.client_email} | Phone: {client.client_phone or 'N/A'}",
                    'url': f"/clients/{client.id}",
                    'date': 'N/A',
                    'date_sort': datetime.min,
                    'status': 'Active' if client.is_active else 'Inactive',
                    'relevance': 0
                })
            
            return results
        except Exception as e:
            print(f"Error searching clients: {e}")
            return []

    @staticmethod
    def _search_payments(search_term, limit):
        """Search in payments"""
        try:
            conditions = or_(
                Payment.pay_ref.ilike(f'%{search_term}%'),
                Payment.payment_status.ilike(f'%{search_term}%')
            )
            
            payments = Payment.query.filter(conditions)\
                .order_by(Payment.pay_date.desc())\
                .limit(limit)\
                .all()
            
            results = []
            for payment in payments:
                results.append({
                    'type': 'Payment',
                    'subtype': payment.pay_type or 'Payment',
                    'title': f"Ref: {payment.pay_ref}",
                    'description': f"Amount: ₱{payment.pay_amount:,.2f} | Method: {payment.pay_method}",
                    'url': "/payments",
                    'date': payment.pay_date.strftime('%Y-%m-%d') if payment.pay_date else 'N/A',
                    'date_sort': payment.pay_date or datetime.min,
                    'status': payment.payment_status,
                    'relevance': 0
                })
            
            return results
        except Exception as e:
            print(f"Error searching payments: {e}")
            return []