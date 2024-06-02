import pytest
import os

from datetime import datetime, timezone, timedelta

from ..database import db
from ..api.models.models import Admin


def test_generate_unique_employee_id (flask_app, create_admin_user) :
    admin, test_uid = create_admin_user
    generated_ids = [admin.generate_unique_employee_id() for _ in range(1000)]

    assert len(generated_ids) == len(set(generated_ids))

def test_hash_pin (flask_app, create_admin_user) :
    # created with pin = 11111
    admin, test_uid = create_admin_user

    # ensuring that pin exists and was not saved unhashed
    assert admin.pin is not None
    assert admin.pin != 11111


def test_check_pin (flask_app, create_admin_user) :
    # created with pin = 11111
    admin, test_uid = create_admin_user

    assert admin.check_pin(11111) is True
    assert admin.check_pin(00000) is False

def test_is_pin_expired (flask_app, create_admin_user) :
    # created with pin = 11111
    admin, test_uid = create_admin_user
    # asserting that pin is not expired upon creation
    assert admin.is_pin_expired() is False

    # manually expiring pin, asserting that method now returns True
    admin.pin_expiration = datetime.now(timezone.utc) - timedelta(days = 1)
    assert admin.is_pin_expired() is True


def test_renew_pin (flask_app, create_admin_user) :
    # created with pin = 11111
    admin, test_uid = create_admin_user

    # should still be expired from previous test
    assert admin.is_pin_expired() is True

    # change pin from 11111 to 12345
    admin.renew_pin(11111, 12345)

    # checking that pin expiration was updated
    assert admin.is_pin_expired() is False

    # checking that pin was actually changed
    assert admin.check_pin(12345) is True
    assert admin.check_pin(11111) is False


# tests for admin controllers
def test_signup (flask_app, mock_firebase) :
    input_data = { 
        'name': 'Test',
        'pin': 12345,
    }
    with mock_firebase('mock_uid') :
        response = flask_app.post('/api/admin/signup/',
            headers = { 'Authorization': f'Bearer mock_uid' },
            json = input_data
        )

    assert response.status_code in [201, 308]
    assert response.json['message'] == 'Admin registered successfully'

    new_admin = Admin.query.filter_by(name = input_data['name']).first()
    assert new_admin is not None
    assert new_admin.firebase_uid == 'mock_uid'
    assert new_admin.employee_id == response.json['employeeId']


@pytest.mark.parametrize('valid_id, valid_pin, expired_pin', [
    (True, True, False), # valid login
    (True, False, None), # invalid credentials
    (True, True, True), # need to update pin
    (False, None, None), # invalid credentials
])
def test_login (flask_app, mock_firebase, valid_id, valid_pin, expired_pin) :
    admin = Admin.query.filter_by(name = 'Test').first()

    if valid_id :
        employee_id = admin.employee_id
    else :
        employee_id = 00000000
    
    if valid_pin :
        pin = 12345
        if expired_pin :
            # setting pin expiration to day before
            admin.pin_expiration = datetime.now(timezone.utc) - timedelta(days = 1)
            db.session.commit()
            db.session.refresh(admin)
    else :
        pin = 00000

    with mock_firebase(admin.firebase_uid) :
        response = flask_app.post('/api/admin/login/',
            headers = { 'Authorization': f'Bearer {admin.firebase_uid}' },
            json = {
                'name': '',
                'employeeId': employee_id,
                'pin': pin
            },
        )


    if valid_id and valid_pin and not expired_pin :
        assert response.status_code == 200
        assert response.json['message'] == 'Admin logged in successfully'
    elif valid_id and valid_pin and expired_pin :
        assert response.status_code == 403
        assert response.json['message'] == 'Pin is expired, please renew pin'
    else :
        assert response.status_code == 401
        assert response.json['message'] == 'Invalid credientials'


@pytest.mark.parametrize('valid_id, valid_pin', [
    (True, True), # successful update
    (True, False), # invalid credentials
    (False, True), # invalid credentials
    (False, False) # invalid credentials
])
def test_update_pin (flask_app, mock_firebase, valid_id, valid_pin) :
    admin = Admin.query.filter_by(name = 'Test').first()

    if valid_id and valid_pin :
        employee_id = admin.employee_id
        old_pin = 12345
    elif valid_id and not valid_pin :
        employee_id = admin.employee_id
        old_pin = 00000
    elif not valid_id and valid_pin :
        employee_id = 00000000
        old_pin = 12345
    else :
        employee_id = 00000000
        old_pin = 00000

    with mock_firebase(admin.firebase_uid) :
        response = flask_app.post('/api/admin/update-pin/',
            headers = { 'Authorization': f'Bearer {admin.firebase_uid}' }, 
            # need to pass values as str to mimic http request body
            json = {
                'employeeId': str(employee_id),
                'oldPin': old_pin,
                'pin': 67890
            }
        )

    if valid_id and valid_pin :
        # check successful response codes and messages
        assert response.status_code == 200
        assert response.json['message'] == 'Pin was updated and admin logged in successfully'

        # refresh admin and assert that pin was updated
        db.session.refresh(admin)
        assert admin.check_pin('67890')
    else :
        assert response.status_code == 401
        assert response.json['error'] == 'Invalid credientials'



@pytest.mark.parametrize('valid_code', [True, False])
def test_login (flask_app, valid_code) :
    code = os.getenv('EMPLOYER_CODE') if valid_code else 00000000
    response = flask_app.post('/api/admin/validate-code/',
        json = {
            'code': code
        }
    )

    assert response.status_code == (200 if valid_code else 400)