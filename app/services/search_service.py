# app/services/search_service.py
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
            if title == search_term:
                relevance += 5
                
            result['relevance'] = relevance
        
        results.sort(key=lambda x: (x['relevance'], x.get('date_sort', datetime.min)), reverse=True)
        return results[:50]
    
    @staticmethod
    def _search_cases(search_term, limit):
        try:
            # FIX: Updated column names (removed 'client_' prefix)
            conditions = or_(
                Case.title.ilike(f'%{search_term}%'),
                Case.case_number.ilike(f'%{search_term}%'),
                Case.case_type.ilike(f'%{search_term}%'),
                Case.violation.ilike(f'%{search_term}%'),
                Case.status.ilike(f'%{search_term}%'),
                Case.client.has(
                    or_(
                        Client.first_name.ilike(f'%{search_term}%'),
                        Client.last_name.ilike(f'%{search_term}%'),
                        Client.company_name.ilike(f'%{search_term}%'), # Added company search
                        func.concat(Client.first_name, ' ', Client.last_name).ilike(f'%{search_term}%')
                    )
                ),
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
        try:
            # FIX: Updated Client column names
            matching_case_ids = db.session.query(Case.id).filter(
                or_(
                    Case.case_number.ilike(f'%{search_term}%'),
                    Case.client.has(
                        or_(
                            Client.first_name.ilike(f'%{search_term}%'),
                            Client.last_name.ilike(f'%{search_term}%'),
                            Client.company_name.ilike(f'%{search_term}%'),
                            func.concat(Client.first_name, ' ', Client.last_name).ilike(f'%{search_term}%')
                        )
                    )
                )
            ).all()

            matching_entry_ids = db.session.query(NotarialEntry.id).join(NotarialEntryParty).filter(
                NotarialEntryParty.party_name.ilike(f'%{search_term}%')
            ).all()
            
            conditions = or_(
                Document.filename.ilike(f'%{search_term}%'),
                Document.document_type.ilike(f'%{search_term}%'),
                Document.notes.ilike(f'%{search_term}%'),
                Document.document_status.ilike(f'%{search_term}%')
            )
            
            if matching_case_ids:
                case_ids_list = [c.id for c in matching_case_ids]
                conditions = or_(conditions, and_(
                    Document.parent_type == 'case',
                    Document.parent_id.in_(case_ids_list)
                ))

            if matching_entry_ids:
                entry_ids_list = [e.id for e in matching_entry_ids]
                conditions = or_(conditions, and_(
                    Document.parent_type == 'notarial_entry',
                    Document.parent_id.in_(entry_ids_list)
                ))
            
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

    # ... (Keep _get_document_context and _search_notarial_entries as they are) ...
    @staticmethod
    def _get_document_context(document):
        try:
            if document.parent_type == 'notarial_entry':
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
        try:
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
        try:
            # FIX: Updated Client column names
            base_conditions = or_(
                TransactionItem.purpose.ilike(f'%{search_term}%'),
                TransactionItem.transaction_type.ilike(f'%{search_term}%'),
                TransactionItem.payment_status.ilike(f'%{search_term}%'),
                TransactionItem.entry_reference.ilike(f'%{search_term}%')
            )
            
            client_conditions = TransactionItem.client.has(
                or_(
                    Client.first_name.ilike(f'%{search_term}%'),
                    Client.last_name.ilike(f'%{search_term}%'),
                    Client.company_name.ilike(f'%{search_term}%'),
                    func.concat(Client.first_name, ' ', Client.last_name).ilike(f'%{search_term}%')
                )
            )
            
            case_client_conditions = TransactionItem.case.has(
                Case.client.has(
                    or_(
                        Client.first_name.ilike(f'%{search_term}%'),
                        Client.last_name.ilike(f'%{search_term}%'),
                        Client.company_name.ilike(f'%{search_term}%'),
                        func.concat(Client.first_name, ' ', Client.last_name).ilike(f'%{search_term}%')
                    )
                )
            )
            
            conditions = or_(base_conditions, client_conditions, case_client_conditions)
            
            transactions = TransactionItem.query.filter(conditions)\
                .order_by(TransactionItem.transaction_date.desc())\
                .limit(limit)\
                .all()
            
            results = []
            for trans in transactions:
                client_name = trans.client.full_name if trans.client else "Unknown Client"
                context_parts = []
                if trans.transaction_type == 'Case' and trans.case:
                    context_parts.append(f"Case #{trans.case.case_number}")
                elif trans.transaction_type == 'Notarial' and trans.entry_reference:
                    context_parts.append(f"Entry Ref: {trans.entry_reference}")
                
                context_str = " | ".join(context_parts)
                
                results.append({
                    'type': 'Transaction',
                    'subtype': trans.transaction_type or 'General',
                    'title': f"{trans.transaction_type}: {trans.purpose}",
                    'description': f"Payer: {client_name} | Amount: ₱{trans.transaction_amount:,.2f} | {context_str}",
                    'url': "/transactions",
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
        try:
            # FIX: Updated column names to match client_mdl.py
            conditions = or_(
                Client.first_name.ilike(f'%{search_term}%'),
                Client.last_name.ilike(f'%{search_term}%'),
                Client.company_name.ilike(f'%{search_term}%'),
                Client.email.ilike(f'%{search_term}%'),
                func.concat(Client.first_name, ' ', Client.last_name).ilike(f'%{search_term}%')
            )
            
            clients = Client.query.filter(and_(conditions, Client.is_active == True))\
                .order_by(Client.id.desc())\
                .limit(limit)\
                .all()
            
            results = []
            for client in clients:
                results.append({
                    'type': 'Client',
                    # FIX: Use correct attribute names for result construction
                    'subtype': client.client_type or 'Client', 
                    'title': client.full_name,
                    'description': f"Email: {client.email} | Phone: {client.phone or 'N/A'}",
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

    # ... (Keep _search_payments as is) ...
    @staticmethod
    def _search_payments(search_term, limit):
        try:
            conditions = or_(
                Payment.pay_ref.ilike(f'%{search_term}%'),
                # Fixed: payment_status doesn't exist on Payment model, removed it to avoid errors
                # Payment.payment_status.ilike(f'%{search_term}%') 
                Payment.pay_method.ilike(f'%{search_term}%')
            )
            
            payments = Payment.query.filter(conditions)\
                .order_by(Payment.pay_date.desc())\
                .limit(limit)\
                .all()
            
            results = []
            for payment in payments:
                results.append({
                    'type': 'Payment',
                    'subtype': payment.pay_method or 'Payment',
                    'title': f"Ref: {payment.pay_ref}",
                    'description': f"Amount: ₱{payment.pay_amount:,.2f} | Method: {payment.pay_method}",
                    'url': "/transactions", # Ideally link to transaction detail
                    'date': payment.pay_date.strftime('%Y-%m-%d') if payment.pay_date else 'N/A',
                    'date_sort': payment.pay_date or datetime.min,
                    'status': 'Paid', # Payments in this table are generally paid records
                    'relevance': 0
                })
            return results
        except Exception as e:
            print(f"Error searching payments: {e}")
            return []