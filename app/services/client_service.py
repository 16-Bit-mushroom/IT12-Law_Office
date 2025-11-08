from app.models.client_model import Client, db

def add_client(name, email, ctype, status, notes):
    new_client = Client(
        name=name,
        email=email,
        client_type=ctype,
        status=status,
        notes=notes
    )
    db.session.add(new_client)
    db.session.commit()

def get_all_clients():
    return Client.query.all()
