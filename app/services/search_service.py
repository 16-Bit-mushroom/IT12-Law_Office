"""
Search Service - Global search functionality across all models
"""
from app.models import db
from app.models.case_mdl import Case
from app.models.document_mdl import Document
from app.models.notarial_entry_mdl import NotarialEntry
from app.models.transaction_mdl import TransactionItem
from app.models.client_mdl import Client
from app.models.payment_mdl import Payment
from app.models.service_mdl import Service
from sqlalchemy import or_, and_
from datetime import datetime
import re


class SearchService:
    
    @staticmethod
    def global_search(query, model_type='all', limit=20):
        """
        Perform global search across all models
        
        Args:
            query (str): Search term
            model_type (str): Type of model to search ('all', 'cases', 'documents', 
                            'notarial', 'transactions', 'clients', 'payments')
            limit (int): Maximum results per model
            
        Returns:
            list: Search results with standardized format
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
        
        # Sort by relevance (search in title gets higher priority)
        for result in results:
            relevance = 0
            title = result.get('title', '').lower()
            description = result.get('description', '').lower()
            
            if search_term in title:
                relevance += 3
            if search_term in description:
                relevance += 1
            
            # Exact matches get highest priority
            if result.get('title', '').lower() == search_term:
                relevance += 5
                
            result['relevance'] = relevance
        
        # Sort by relevance and then by date (newest first)
        results.sort(key=lambda x: (x['relevance'], x.get('date_sort', datetime.min)), reverse=True)
        
        return results[:50]  # Overall limit
    
    @staticmethod
    def _search_cases(search_term, limit):
        """Search in cases"""
        try:
            # Build search conditions
            conditions = or_(
                Case.title.ilike(f'%{search_term}%'),
                Case.case_number.ilike(f'%{search_term}%'),
                Case.case_type.ilike(f'%{search_term}%'),
                Case.violation.ilike(f'%{search_term}%'),
                Case.status.ilike(f'%{search_term}%')
            )
            
            cases = Case.query.filter(conditions)\
                .order_by(Case.engagement_date.desc())\
                .limit(limit)\
                .all()
            
            results = []
            for case in cases:
                results.append({
                    'type': 'Case',
                    'subtype': case.case_type or 'Case',
                    'title': f"{case.case_number}: {case.title}",
                    'description': f"{case.violation or 'No violation specified'} | Status: {case.status}",
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
        """Search in documents"""
        try:
            conditions = or_(
                Document.filename.ilike(f'%{search_term}%'),
                Document.document_type.ilike(f'%{search_term}%'),
                Document.notes.ilike(f'%{search_term}%'),
                Document.document_status.ilike(f'%{search_term}%')
            )
            
            documents = Document.query.filter(conditions)\
                .order_by(Document.uploaded_at.desc())\
                .limit(limit)\
                .all()
            
            results = []
            for doc in documents:
                # Get context name
                context_name = SearchService._get_document_context(doc)
                
                results.append({
                    'type': 'Document',
                    'subtype': doc.document_type or 'Document',
                    'title': doc.filename,
                    'description': f"{doc.notes or 'No description'} | Status: {doc.document_status} | {context_name}",
                    'url': f"/documents/download/{doc.id}",
                    'date': doc.uploaded_at.strftime('%Y-%m-%d'),
                    'date_sort': doc.uploaded_at,
                    'status': doc.document_status,
                    'file_size': doc.formatted_file_size,
                    'relevance': 0
                })
            
            return results
        except Exception as e:
            print(f"Error searching documents: {e}")
            return []
    
    @staticmethod
    def _get_document_context(document):
        """Get human-readable context for a document"""
        try:
            if document.parent_type == 'notarial_entry':
                from app.models.notarial_entry_mdl import NotarialEntry
                entry = NotarialEntry.query.get(document.parent_id)
                if entry:
                    return f"Notarial Entry #{entry.not_entry_num}"
            
            elif document.parent_type == 'case':
                case = Case.query.get(document.parent_id)
                if case:
                    return f"Case #{case.case_number}"
            
            elif document.parent_type == 'client':
                client = Client.query.get(document.parent_id)
                if client:
                    return f"Client: {client.full_name}"
            
            return f"{document.parent_type} #{document.parent_id}"
        except:
            return "Unknown Context"
    
    @staticmethod
    def _search_notarial_entries(search_term, limit):
        """Search in notarial entries"""
        try:
            from app.models.notarial_entry_mdl import NotarialEntry
            
            conditions = or_(
                NotarialEntry.not_title.ilike(f'%{search_term}%'),
                NotarialEntry.not_entry_num.ilike(f'%{search_term}%'),
                NotarialEntry.not_type_act.ilike(f'%{search_term}%'),
                NotarialEntry.not_book_num.ilike(f'%{search_term}%')
            )
            
            entries = NotarialEntry.query.filter(conditions)\
                .order_by(NotarialEntry.not_date.desc())\
                .limit(limit)\
                .all()
            
            results = []
            for entry in entries:
                # Get party names
                party_names = []
                if entry.parties:
                    party_names = [p.party_name for p in entry.parties[:2]]
                
                results.append({
                    'type': 'Notarial',
                    'subtype': entry.not_type_act or 'Notarial Entry',
                    'title': f"Entry #{entry.not_entry_num}: {entry.not_title}",
                    'description': f"Book: {entry.not_book_num}, Page: {entry.not_page_num} | Parties: {', '.join(party_names) if party_names else 'No parties'}",
                    'url': f"/notarial-entries/{entry.id}",
                    'date': entry.not_date.strftime('%Y-%m-%d'),
                    'date_sort': entry.not_date,
                    'status': entry.transaction_status if hasattr(entry, 'transaction_status') else 'N/A',
                    'fee': float(entry.not_fee) if entry.not_fee else 0,
                    'relevance': 0
                })
            
            return results
        except Exception as e:
            print(f"Error searching notarial entries: {e}")
            return []
    
    @staticmethod
    def _search_transactions(search_term, limit):
        """Search in transactions"""
        try:
            conditions = or_(
                TransactionItem.purpose.ilike(f'%{search_term}%'),
                TransactionItem.transaction_type.ilike(f'%{search_term}%'),
                TransactionItem.payment_status.ilike(f'%{search_term}%')
            )
            
            transactions = TransactionItem.query.filter(conditions)\
                .order_by(TransactionItem.transaction_date.desc())\
                .limit(limit)\
                .all()
            
            results = []
            for trans in transactions:
                client_name = trans.client.full_name if trans.client else "Unknown Client"
                
                results.append({
                    'type': 'Transaction',
                    'subtype': trans.transaction_type or 'Transaction',
                    'title': f"{trans.transaction_type}: {trans.purpose}",
                    'description': f"Client: {client_name} | Amount: ₱{trans.transaction_amount:,.2f} | Status: {trans.payment_status}",
                    'url': "/transactions",  # No single view, go to list
                    'date': trans.transaction_date.strftime('%Y-%m-%d') if trans.transaction_date else 'N/A',
                    'date_sort': trans.transaction_date or datetime.min,
                    'status': trans.payment_status,
                    'amount': float(trans.transaction_amount) if trans.transaction_amount else 0,
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
                Client.client_phone.ilike(f'%{search_term}%'),
                Client.client_address.ilike(f'%{search_term}%')
            )
            
            # Only active clients
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
                    'description': f"Email: {client.client_email} | Phone: {client.client_phone or 'N/A'} | Address: {client.client_address}",
                    'url': "#",  # No client detail page yet
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
                Payment.pay_method.ilike(f'%{search_term}%'),
                Payment.pay_type.ilike(f'%{search_term}%'),
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
                    'title': f"Payment Ref: {payment.pay_ref}",
                    'description': f"Method: {payment.pay_method} | Amount: ₱{payment.pay_amount:,.2f} | Status: {payment.payment_status}",
                    'url': "/payments",  # No single view, go to list
                    'date': payment.pay_date.strftime('%Y-%m-%d') if payment.pay_date else 'N/A',
                    'date_sort': payment.pay_date or datetime.min,
                    'status': payment.payment_status,
                    'amount': float(payment.pay_amount) if payment.pay_amount else 0,
                    'relevance': 0
                })
            
            return results
        except Exception as e:
            print(f"Error searching payments: {e}")
            return []
    
    @staticmethod
    def get_search_suggestions(query, limit=5):
        """Get quick search suggestions for live search"""
        if not query or len(query.strip()) < 2:
            return []
        
        search_term = query.strip().lower()
        suggestions = []
        
        # Get a few results from each category
        all_results = SearchService.global_search(search_term, 'all', limit=3)
        
        # Format suggestions
        for result in all_results[:limit]:
            suggestions.append({
                'text': result['title'],
                'type': result['type'],
                'url': result['url'],
                'description': result['description'][:100] + '...' if len(result['description']) > 100 else result['description']
            })
        
        return suggestions