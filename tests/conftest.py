from flask import make_response, redirect
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.sql.expression import delete

from ..app import create_app
from ..database import db
from ..api.utils.set_auth_cookies import set_tokens_in_cookies
from ..api.models import User, Admin, Address, Product, Portion, Cart_Item, Order, Task

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
            Task,
            Order,
            Address,
            User,
            Admin,
            Portion,
            Product
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
    admin = Admin(
        name = 'Admin',
        email = 'admin@gmail.com',
        password = 'password',
        pin = 11111,
    )
    db.session.add(admin)
    db.session.commit()

    return admin

@pytest.fixture(scope = 'session')
def create_second_admin_user () :    
    admin = Admin(
        name = 'Second Admin',
        email = 'secondadmin@gmail.com',
        password = 'password',
        pin = 11111,
    )
    db.session.add(admin)
    db.session.commit()

    return admin

@pytest.fixture(scope = 'session')
def admin_login (flask_app, create_admin_user) :
    admin = create_admin_user

    response = flask_app.post('/api/admin/login/',
        json = {
            'employeeId': admin.employee_id,
            'password': 'password',
            'pin': 11111,
        },
    )

@pytest.fixture(scope = 'session')
def create_client_user () :
    user = User(
        name = 'Client',
        email = 'client@gmail.com',
        password = 'password',
    )
    db.session.add(user)
    db.session.commit()

    return user

@pytest.fixture(scope = 'session')
def user_login (flask_app, create_client_user) :
    user = create_client_user

    flask_app.post('/api/user/login',
        json = {
            'email': user.email,
            'password': 'password',
            'localStorageCart': None
        },
    )
