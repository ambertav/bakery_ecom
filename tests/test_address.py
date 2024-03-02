import pytest, unittest, datetime
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError, DataError

from ..database import db
from ..api.models.models import Address, Order, Order_Status, Ship_Method, Pay_Status


@pytest.fixture(scope = 'module')
def seed_addresses (flask_app, create_client_user) :
    user, test_uid = create_client_user

    address_data = [{
        'first_name': 'Emily',
        'last_name': 'Smith',
        'street': '123 Main St',
        'city': 'Anytown',
        'state': 'NY',
        'zip': '10001'
    },
    {
        'first_name': 'Sophia', 
        'last_name': 'Williams',
        'street': '456 Elm St',
        'city': 'Sometown',
        'state': 'CA',
        'zip': '90001'
    },
    {
        'first_name': 'Alice',
        'last_name': 'Johnson',
        'street': '789 Oak St',
        'city': 'Othertown',
        'state': 'TX',
        'zip': '75001'
    }]

    for address in address_data :
        address['default'] = False
        address['user_id'] = user.id

    session = db.session()

    try:
        # insert address in bulk
        session.bulk_insert_mappings(Address, address_data)
        session.commit()

        # returns list of all addresses for use throughout module tests
        # orders default address first in list
        yield Address.query.filter_by(user_id = user.id).order_by(desc(Address.default)).all()

    finally:
        session.rollback()
        session.close()


# testing zip code validation
@pytest.mark.parametrize('first_name, last_name, street, city, state, zip, default, valid', [
    ('Jane', 'Doe', '123 Pytest Street', 'New York', 'NY', '10000', True, True), # valid zip, successful
    ('John', 'Doe', '789 Unittest Street', 'Los Angeles', 'CA', '1abc1', False, False), # invalid zip, due to letters
    ('John', 'Doe', '000 Robot Street', 'Los Angeles', 'CA', '123', False, False), # invalid zip, too short (integrity error)
    ('John', 'Doe', '111 Robot Street', 'Los Angeles', 'CA', '456789', False, False), # invalid zip, too long (data error)
])
def test_address_validation (flask_app, create_client_user, first_name, last_name, street, city, state, zip, default, valid) :
    # create user
    user, test_uid = create_client_user

    if valid :       
        # base case with valid data, should create address
        create_and_add_address(first_name, last_name, street, city, state, zip, default, user.id)
        added_address = Address.query.filter_by(street = street).first()
        assert added_address is not None
    
    else :
        # testing column constraints by asserting presence of IntegrityError
        with pytest.raises((IntegrityError, DataError)) as error :
            create_and_add_address(first_name, last_name, street, city, state, zip, default, user.id)

        db.session.rollback() # rollback failed transaction in database 
        assert error.type in (IntegrityError, DataError) # assert IntegrityError


@pytest.mark.parametrize('requesting_default', (True, False))
def test_get_address (flask_app, create_client_user, seed_addresses, requesting_default) :
    # create user and get list of addresses
    user, test_uid = create_client_user
    addresses = seed_addresses

    # if user requesting default, query param of default=true
    query_params = { 'default': 'true' } if requesting_default else {}

    response = flask_app.get('/api/address/', headers = {'Authorization': f'Bearer {test_uid}'}, query_string = query_params)
    
    assert response.status_code in [200, 308]

    # if default=true query param
    if requesting_default :
        # query for default address, assert that its same as response 
        default_address = Address.query.filter_by(user_id = user.id, default = True).all()
        unittest.TestCase().assertDictEqual(default_address[0].as_dict(), response.json['addresses'])

    else :
        # asserting that response sends all the addresses
        assert len(response.json['addresses']) == len(addresses)


@pytest.mark.parametrize('valid_address', [(True), (False)])
def test_update_default (flask_app, create_client_user, seed_addresses, valid_address) :
    # create user and get list of addresses
    user, test_uid = create_client_user
    addresses = seed_addresses

    previous_default = addresses[0]

    # if valid test
    if valid_address :
        # get id from first not default address
        new_default = Address.query.filter_by(user_id = user.id, default = False).first()
        address_id = new_default.id
    else :
        # otherwise, initialize id with an invalid id
        address_id = 0

    response = flask_app.put(f'/api/address/default/{address_id}', headers = {'Authorization': f'Bearer {test_uid}'})

    if valid_address :
        assert response.status_code == 200
        assert response.json['message'] == 'Default address updated successfully'

        # query for new default address
        updated_default = Address.query.filter_by(user_id = user.id, default = True).all()
        # assert the default address was updated and there is only one
        assert len(updated_default) is 1
        assert updated_default[0].id == new_default.id and updated_default[0].id != previous_default.id

    else :
        assert response.status_code == 404
        assert response.json['error'] == 'Address not found'


@pytest.mark.parametrize('valid_id, is_default, used_for_order', [
    (True, True, False), # valid id, is default, not used for order --> should delete and make next in line default
    (True, False, False), # valid id, not default, not used for order --> should delete
    (True, False, True), # valid id, not default, used for order --> 400 error, violates not null in order table
    (False, None, None) # invalid id, 404 not found
])
def test_delete_address (flask_app, create_client_user, seed_addresses, valid_id, is_default, used_for_order) :
    # create user and get list of addresses
    user, test_uid = create_client_user
    addresses = seed_addresses

    if valid_id :
        if is_default :
            address_id = addresses[0].id
        else :
            # query for first not default address to use id for valid and non default cases
            address = Address.query.filter_by(user_id = user.id, default = False).first()
            address_id = address.id
             
            if used_for_order :
                create_order_and_associate_address(address_id, user.id)

    else :
        address_id = 0

    response = flask_app.delete(f'/api/address/{address_id}/delete', headers = {'Authorization': f'Bearer {test_uid}'})

    if valid_id :
        if used_for_order :
            assert response.status_code == 400
            assert response.json['error'] == 'Violates not null constraint'

        else :
            # if valid and not used for order, should succeed
            assert response.status_code == 200
            assert response.json['message'] == 'Address deleted successfully'

            # query for deleted address should be None
            deleted_address = Address.query.get(address_id)
            assert deleted_address is None

            if is_default :
                # if default, find new default and assert it doesn't match the previous default
                new_default = Address.query.filter_by(user_id = user.id, default = True).all()
                assert len(new_default) is 1
                assert new_default[0].id != address_id
    else :
        assert response.status_code == 404
        assert response.json['error'] == 'Address not found'
    



# ---- helpers ----

def create_and_add_address (first_name, last_name, street, city, state, zip, default, user_id) :
    address = Address(
        first_name = first_name,
        last_name = last_name,
        street = street,
        city = city,
        state = state,
        zip = zip,
        default = default,
        user_id = user_id
    )

    db.session.add(address)
    db.session.commit()

    return address


def create_order_and_associate_address (address_id, user_id) :
    order = Order(
        user_id = user_id,
        total_price = 10.00,
        date = datetime.datetime.now(),
        status = Order_Status.PENDING,
        stripe_payment_id = None,
        shipping_method = Ship_Method.STANDARD,
        payment_status = Pay_Status.PENDING,
        shipping_address_id = address_id
    )

    db.session.add(order)
    db.session.commit()

    return order