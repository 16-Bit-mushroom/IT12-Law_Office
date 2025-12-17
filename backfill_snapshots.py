import json
from datetime import datetime
from app import create_app, db
from app.models.case_mdl import Case

app = create_app()

def backfill_snapshots():
    with app.app_context():
        print("🛡️ Starting Snapshot Backfill for Completed Cases...")
        
        # Find completed cases that DON'T have a snapshot yet
        cases = Case.query.filter(Case.status == 'completed', Case.client_snapshot == None).all()
        
        count = 0
        for case in cases:
            if case.client:
                print(f"   -> Freezing data for Case: {case.case_number}")
                
                # Get Safe Address
                addr = getattr(case.client, 'full_address', '')
                
                # Create Snapshot Data
                snapshot = {
                    "frozen_at": datetime.now().strftime('%Y-%m-%d'),
                    "name": case.client.full_name,
                    "email": case.client.email,
                    "phone": case.client.phone,
                    "address": addr,
                    "representative": getattr(case.client, 'designated_representative', None)
                }
                
                # Save to Database
                case.client_snapshot = json.dumps(snapshot)
                count += 1
        
        db.session.commit()
        print(f"✅ Success! {count} completed cases are now frozen and protected from changes.")

if __name__ == '__main__':
    backfill_snapshots()