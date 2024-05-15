import pytest, datetime, uuid
from sqlalchemy.sql.expression import delete
from datetime import datetime, timezone

from ..app import create_app
from ..database import db
from ..api.models.models import User, Admin, Address, Product, Cart_Item, Order, Task

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

@pytest.fixture(scope = 'session', autouse = True)
def database_cleanup (flask_app) :
    # yield for tests to complete
    yield 

    # start database connection
    engine = db.get_engine(app = flask_app)
    connection = engine.connect()

    # start transaction
    transaction = connection.begin()

    try :
        # list of tables in order for successful cascade deletion
        tables_in_cascade_deletion_order = [
            Cart_Item,
            Order,
            Task,
            Address,
            User,
            Admin,
            Product,
        ]

        # loop through and delete from each table
        for table in tables_in_cascade_deletion_order :
            connection.execute(delete(table))

        # commit transaction
        transaction.commit()

    except Exception as error :
        transaction.rollback() # if error, rollback
        raise error
    
    finally :
        # close connection
        connection.close()


@pytest.fixture(scope = 'session')
def create_admin_user () :
    admin_uid = generate_firebase_uid()
    
    admin = Admin(
        name = 'Admin',
        pin = 12345,
        firebase_uid = admin_uid,
        created_at = datetime.now(timezone.utc)
    )
    db.session.add(admin)
    db.session.commit()

    return admin, admin_uid

@pytest.fixture(scope = 'session')
def create_client_user () :
    user_uid = generate_firebase_uid()

    user = User(
        name = 'Client',
        firebase_uid = user_uid,
        stripe_customer_id = None,
        created_at = datetime.now(timezone.utc)
    )
    db.session.add(user)
    db.session.commit()

    return user, user_uid