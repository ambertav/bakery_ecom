import pytest, datetime, uuid, firebase_admin
from firebase_admin import auth

from ..app import create_app
from ..database import db
from ..api.models.models import User, Role

def generate_firebase_uid():
    uid = str(uuid.uuid4())
    firebase_uid = uid.replace('-', '_')
    return firebase_uid

@pytest.fixture(scope = 'session')
def flask_app () :
    app = create_app()
    client = app.test_client()

    ctx = app.test_request_context()
    ctx.push()

    yield client

    ctx.pop()

@pytest.fixture(scope = 'session')
def create_admin_user () :
    test_uid = generate_firebase_uid()
    
    user = User(
        name = 'Admin',
        firebase_uid = test_uid,
        role = Role.ADMIN,
        stripe_customer_id = None,
        billing_address = None,
        shipping_address = None,
        created_at = datetime.datetime.utcnow()
    )
    db.session.add(user)
    db.session.commit()

    return user, test_uid

@pytest.fixture(scope = 'session')
def create_client_user () :
    test_uid = generate_firebase_uid()

    user = User(
        name = 'Client',
        firebase_uid = test_uid,
        role = Role.CLIENT,
        stripe_customer_id = None,
        billing_address = None,
        shipping_address = None,
        created_at = datetime.datetime.utcnow()
    )
    db.session.add(user)
    db.session.commit()

    return user, test_uid