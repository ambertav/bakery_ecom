import pytest, datetime, uuid
from sqlalchemy.sql.expression import delete

from ..app import create_app
from ..database import db
from ..api.models.models import User, Role, Address, Product, Cart_Item, Order

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
            Address,
            User,
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