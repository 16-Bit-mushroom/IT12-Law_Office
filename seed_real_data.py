import random
from datetime import datetime, timedelta, timezone
from faker import Faker
from app import create_app, db
from sqlalchemy.exc import IntegrityError

# Import All Models
from app.models.user_model import User
from app.models.client_mdl import Client
from app.models.case_mdl import Case
from app.models.document_mdl import Document
from app.models.notarial_entry_mdl import NotarialEntry, NotarialEntryParty
from app.models.schedule_mdl import Schedule
from app.models.transaction_mdl import TransactionItem
from app.models.payment_mdl import Payment
from app.models.service_mdl import Service 

# Initialize Faker with Philippines Locale
fake = Faker('en_PH')
app = create_app()

# --- CONSTANTS & CONFIGURATION ---
DATE_RANGE_MONTHS = 6
PHT = timezone(timedelta(hours=8))

# 1. ONLY TEMPLATED ACTS
PH_NOTARIAL_ACTS = [
    'Affidavit of Loss',
    'Joint Affidavit of Two Disinterested Persons',
    'Special Power of Attorney',
    'Affidavit of No Income',
    'Affidavit of Undertaking'
]

# 2. PH CONTEXT VIOLATIONS (Category, Type, Violation)
PH_CASE_DATA = {
    'Criminal': [
        ('Estafa', 'Art. 315, Revised Penal Code'),
        ('Violation of BP 22', 'Bouncing Checks Law'),
        ('Qualified Theft', 'Art. 310, Revised Penal Code'),
        ('Reckless Imprudence', 'Damage to Property with Physical Injuries'),
        ('Violation of RA 9165', 'Sec. 5 (Sale) & Sec. 11 (Possession)'),
        ('Cyber Libel', 'Cybercrime Prevention Act of 2012')
    ],
    'Civil': [
        ('Collection of Sum of Money', 'Unpaid Loan Obligation'),
        ('Ejectment', 'Unlawful Detainer'),
        ('Breach of Contract', 'Specific Performance'),
        ('Damages', 'Quasi-Delict / Tort'),
        ('Recovery of Possession', 'Accion Publiciana')
    ],
    'Family': [
        ('Declaration of Nullity', 'Psychological Incapacity (Art. 36)'),
        ('Petition for Support', 'Violence Against Women & Children (RA 9262)'),
        ('Adoption', 'Domestic Adoption Act'),
        ('Legal Separation', 'Abandonment')
    ],
    'Labor': [
        ('Illegal Dismissal', 'Termination without Just Cause'),
        ('Money Claims', 'Non-payment of 13th Month / Overtime'),
        ('Constructive Dismissal', 'Forced Resignation')
    ],
    'Administrative': [
        ('Land Registration', 'Petition for Original Registration'),
        ('Notarial Commission', 'Petition for Renewal of Commission')
    ]
}

NOTARIAL_FEES = [150, 200, 250, 300, 350, 500, 1000]
PAYMENT_METHODS = ['Cash', 'GCash', 'Check', 'Bank Transfer']
DOC_STATUSES_NO_PENDING = ['Completed', 'Lacking', 'For Signature', 'Draft']

def to_roman(n):
    """Convert integer to Roman numeral for Book Numbers"""
    val = [
        1000, 900, 500, 400,
        100, 90, 50, 40,
        10, 9, 5, 4,
        1
    ]
    syb = [
        "M", "CM", "D", "CD",
        "C", "XC", "L", "XL",
        "X", "IX", "V", "IV",
        "I"
    ]
    roman_num = ''
    i = 0
    while  n > 0:
        for _ in range(n // val[i]):
            roman_num += syb[i]
            n -= val[i]
        i += 1
    return roman_num

def get_random_date():
    end = datetime.now()
    start = end - timedelta(days=30 * DATE_RANGE_MONTHS)
    return fake.date_between(start_date=start, end_date=end)

def generate_valid_phone():
    return f"09{fake.numerify('#########')}"

def generate_case_number(date_obj):
    city_code = random.choice(['DVO', 'MNL', 'CEB', 'TAG', 'QZN'])
    year = date_obj.strftime('%y')
    num = fake.unique.numerify('#####')
    suffix = random.choice(['CV', 'CR', 'SP', 'LBR', 'ADM'])
    return f"R-{city_code}-{year}-{num}-{suffix}"

def generate_payment_ref(method):
    if method == 'GCash': return fake.numerify('#############') # 13 digits
    if method == 'Check': return fake.numerify('##########')
    if method == 'Bank Transfer': return fake.bothify('TRX-#######').upper()
    return f"OR-{fake.numerify('#####')}"

def ensure_services_exist():
    services = [
        {'name': 'Notarization', 'fee': 200},
        {'name': 'Case Acceptance Fee', 'fee': 50000}
    ]
    created = []
    for s in services:
        svc = Service.query.filter_by(service_name=s['name']).first()
        if not svc:
            svc = Service(service_name=s['name'], fee=s['fee'], is_notarization=(s['name']=='Notarization'))
            db.session.add(svc)
            db.session.flush()
        created.append(svc)
    db.session.commit()
    return created

def seed_database():
    with app.app_context():
        print("🇵🇭 STARTING COMPLETE SEED (Atty. Jumao-as Edition)...")

        # 1. SETUP SPECIFIC ATTORNEY (Admin)
        target_email = 'rodrigo@jumaoas-law.com'
        atty = User.query.filter_by(email=target_email).first()
        
        if not atty:
            print("... Creating Atty. Rodrigo B. Jumao-as")
            atty = User(
                username='Atty. Rodrigo',
                email=target_email,
                role='admin',
                is_admin=True,
                is_active=True,
                contact_number='09171234567'
            )
            atty.set_password('password123')
            db.session.add(atty)
            db.session.commit()
        
        # 2. SERVICES
        services = ensure_services_exist()
        notary_service = next(s for s in services if s.service_name == 'Notarization')
        case_service = next(s for s in services if s.service_name == 'Case Acceptance Fee')

        # 3. CLIENTS
        print(f"... Checking/Creating Clients")
        clients = []
        
        # 3.1 Walk-in Client (ID 1) - Required for Notarials
        walk_in = db.session.get(Client, 1) 
        if not walk_in:
            print("... Creating 'Walk-in Client' at ID #1")
            walk_in = Client(
                client_type='individual',
                first_name='General',
                last_name='Public',
                email='walkin@lawoffice.com',
                phone='00000000000',
                street_address='Office Walk-in',
                city='Davao City',
                is_active=True
            )
            db.session.add(walk_in)
            db.session.commit()
        clients.append(walk_in)

        # 3.2 Regular Clients (Filipino Names)
        print(f"... Generating 35 Regular Filipino Clients")
        for _ in range(35):
            is_corp = random.random() < 0.2
            client = Client(
                client_type='corporate' if is_corp else 'individual',
                email=fake.unique.email(),
                phone=generate_valid_phone(),
                street_address=fake.address().split('\n')[0],
                city=fake.city(),
                is_active=True
            )
            if is_corp:
                client.company_name = f"{fake.company()} {random.choice(['Inc.', 'Corp.', 'Holdings'])}"
                client.designated_representative = fake.name()
            else:
                client.first_name = fake.first_name()
                client.last_name = fake.last_name()
                # Faker en_PH usually gives good Filipino names
            
            db.session.add(client)
            clients.append(client)
        db.session.commit()

        # 4. NOTARIAL ENTRIES (Strict Logic)
        print("... Creating Notarials (Templates Only, Roman Books, Varied Payments)")
        for _ in range(60):
            n_date = get_random_date()
            
            # VARIATIONS
            act = random.choice(PH_NOTARIAL_ACTS)
            fee = random.choice(NOTARIAL_FEES)
            method = random.choice(PAYMENT_METHODS)
            
            # ROMAN BOOK / PAGE > 2
            book_num = to_roman(random.randint(1, 20)) # I to XX
            page_num = str(random.randint(2, 100))     # Always > 1
            
            # A. Transaction (Strictly Client ID 1)
            trans = TransactionItem(
                client_id=1,
                service_id=notary_service.id,
                transaction_type='Notarial',
                purpose=f"Notarial Fee - {act}",
                transaction_amount=fee,
                payment_status='Paid',
                transaction_date=n_date
            )
            db.session.add(trans)
            db.session.flush()

            # B. Payment
            pay_ref = generate_payment_ref(method)
            pay = Payment(
                transaction_item_id=trans.id,
                pay_method=method,
                pay_ref=pay_ref,
                pay_amount=fee,
                pay_date=n_date
            )
            db.session.add(pay)

            # C. Entry
            entry = NotarialEntry(
                not_entry_num=str(random.randint(1, 1000)),
                not_page_num=page_num,
                not_book_num=book_num,
                not_series=str(n_date.year),
                not_title=act,
                not_date=n_date,
                not_type_act="Notarial Act",
                not_fee=fee,
                not_fee_or=pay_ref,
                transaction_status='paid',
                transaction_item_id=trans.id
            )
            db.session.add(entry)
            db.session.flush()
            
            # D. Parties (Handle Joint Affidavit Logic)
            
            # Party 1 (Always present)
            p1_name = f"{fake.first_name()} {fake.last_name()}"
            db.session.add(NotarialEntryParty(
                notarial_entry_id=entry.id,
                party_name=p1_name,
                party_address=fake.city(),
                citizenship='Filipino',
                party_id_type='Passport',
                party_id_number=fake.numerify('P#######A')
            ))
            
            # Party 2 (REQUIRED if Joint Affidavit)
            if "Joint" in act or "Two" in act:
                p2_name = f"{fake.first_name()} {fake.last_name()}"
                db.session.add(NotarialEntryParty(
                    notarial_entry_id=entry.id,
                    party_name=p2_name,
                    party_address=fake.city(),
                    citizenship='Filipino',
                    party_id_type='UMID',
                    party_id_number=fake.numerify('000-########-#')
                ))

        db.session.commit()

        # 5. CASES (Assigned to Atty. Jumao-as)
        print("... Creating Cases (Assigned to Atty. Jumao-as)")
        # Distribution: 15 Active, 8 Completed, 7 Pending
        scenarios = ['active']*15 + ['completed']*8 + ['pending']*7
        
        for status in scenarios:
            client = random.choice(clients[1:]) # Skip walk-in
            c_date = get_random_date()
            
            # Pick Contextual PH Data
            cat = random.choice(list(PH_CASE_DATA.keys()))
            type_tuple = random.choice(PH_CASE_DATA[cat])
            c_type = type_tuple[0]
            violation = type_tuple[1]
            
            # Generate Realistic Titles
            if cat == 'Criminal':
                title = f"People vs. {fake.last_name()}" 
            elif cat == 'Family':
                title = f"In Re: {c_type.split('(')[0]} - {client.last_name}"
            elif cat == 'Administrative':
                title = f"Re: {c_type} of {client.last_name}"
            else:
                title = f"{client.last_name} vs. {fake.company()}"
            
            case = Case(
                case_number=generate_case_number(c_date),
                title=title,
                case_category=cat,
                case_type=c_type,
                violation=violation, # Specific PH Violation
                status=status,
                engagement_date=c_date,
                client_id=client.id,
                assigned_attorney_id=atty.id # Assigned to Atty. Jumao-as
            )
            
            # LOGIC: Filing Date
            # Active/Completed MUST have Filing Date. Pending MUST NOT.
            if status in ['active', 'completed']:
                case.filing_date = c_date + timedelta(days=random.randint(5, 20))
            else: # Pending
                case.filing_date = None 

            db.session.add(case)
            db.session.flush()

            # LOGIC: Financials (Total Legal Fee & Acceptance Fee)
            # Active/Completed MUST be Paid. Pending is unpaid/partial.
            pay_status = 'Paid' if status != 'pending' else random.choice(['Pending', 'Partial'])
            fee_amount = 50000
            
            trans = TransactionItem(
                client_id=client.id,
                service_id=case_service.id,
                case_id=case.id,
                transaction_type='Case',
                purpose="Total Legal Fee", # <--- FIXED
                transaction_amount=fee_amount,
                transaction_date=c_date,
                payment_status=pay_status
            )
            db.session.add(trans)
            db.session.flush()

            if pay_status == 'Paid':
                db.session.add(Payment(
                    transaction_item_id=trans.id, 
                    pay_method=random.choice(PAYMENT_METHODS), 
                    pay_ref=generate_payment_ref('Check'), 
                    pay_amount=fee_amount, 
                    pay_date=c_date,
                    notes="Acceptance Fee" # <--- FIXED
                ))
            elif pay_status == 'Partial':
                db.session.add(Payment(
                    transaction_item_id=trans.id, 
                    pay_method='GCash', 
                    pay_ref=generate_payment_ref('GCash'), 
                    pay_amount=20000, 
                    pay_date=c_date,
                    notes="Partial Acceptance"
                ))

            # LOGIC: Documents
            # No 'Pending' status. Only Completed, Lacking, For Signature.
            for _ in range(random.randint(2, 5)):
                if status == 'completed':
                    doc_stat = 'Completed'
                elif status == 'active':
                    doc_stat = random.choice(['Completed', 'For Signature', 'Completed'])
                else: # Pending
                    doc_stat = random.choice(['Lacking', 'Draft', 'For Signature']) # Removed 'Pending'
                
                db.session.add(Document(
                    filename=f"{random.choice(['Judicial Affidavit', 'Motion', 'Position Paper', 'Reply'])} - {fake.word()}.pdf",
                    file_path="uploads/dummy.pdf",
                    parent_type='case',
                    parent_id=case.id,
                    document_status=doc_stat,
                    uploaded_at=c_date + timedelta(days=random.randint(1, 10))
                ))

        db.session.commit()

        # 6. DEADLINES (More items, mix of urgent and future)
        print("... Setting 12+ Deadlines")
        active_cases = Case.query.filter_by(status='active').all()
        if active_cases:
            today = datetime.now()
            
            # Urgent (Trigger Dashboard Popup)
            db.session.add(Schedule(title="URGENT: Submit Formal Offer of Evidence", deadline=today, priority='high', case_id=active_cases[0].id))
            db.session.add(Schedule(title="Hearing: Pre-Trial Conference", deadline=today+timedelta(days=1), priority='high', case_id=active_cases[-1].id))
            
            # Future (Trigger "Upcoming Deadlines" List)
            titles = [
                "Submission of Judicial Affidavit", "Mediation Conference", "Cross-Examination of Witness",
                "Filing of Comment", "Reply to Opposition", "Promulgation of Judgment",
                "Motion for Reconsideration", "Pre-Trial Briefing", "Status Hearing", "Client Meeting"
            ]
            
            for i in range(10):
                future_date = today + timedelta(days=random.randint(3, 60))
                db.session.add(Schedule(
                    title=titles[i], 
                    deadline=future_date, 
                    priority='normal', 
                    case_id=random.choice(active_cases).id
                ))

        # 7. RECYCLE BIN (Soft Delete Items)
        print("... Populating Recycle Bin")
        
        # Soft Delete a Client
        del_client = Client(client_type='individual', first_name='Deleted', last_name='User', email='del@test.com', is_active=False, deleted_at=datetime.now())
        db.session.add(del_client)
        
        # Soft Delete a Case
        del_case = Case(
            case_number="R-DEL-24-00000-XX", title="Archived Case vs. World", case_category="Civil", case_type="Damages",
            status="archived", engagement_date=datetime.now(), client_id=clients[1].id, assigned_attorney_id=atty.id, deleted_at=datetime.now()
        )
        db.session.add(del_case)
        
        # Soft Delete a Document
        del_doc = Document(
            filename="Mistake_Upload.pdf", file_path="uploads/dummy.pdf", parent_type='case', parent_id=1,
            document_status="Draft", deleted_at=datetime.now()
        )
        db.session.add(del_doc)

        db.session.commit()
        print("\n✅ SUCCESS: Full Data Seeding Complete!")
        print("   - Atty. Rodrigo created & assigned.")
        print("   - Notarial Books used Roman Numerals.")
        print("   - Case Logic Enforced (Active=Filed, Pending=Not Filed).")
        print("   - Financials use 'Total Legal Fee'.")

if __name__ == '__main__':
    try:
        seed_database()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")