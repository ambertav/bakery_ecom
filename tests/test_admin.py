import pytest
import os

from unittest.mock import patch

from datetime import datetime, timezone, timedelta

from ..database import db
from ..api.models import Admin


def test_generate_unique_employee_id (create_admin_user) :
    admin = create_admin_user
    generated_ids = [admin._generate_unique_employee_id() for _ in range(1000)]

    assert len(generated_ids) == len(set(generated_ids))

def test_hash_password (create_admin_user) :
    # created with password = 'password'
    admin = create_admin_user

    assert admin.password != 'password'
    assert isinstance(admin.password, bytes)

def test_hash_pin (create_admin_user) :
    # created with pin = 11111
    admin = create_admin_user

    # ensuring that pin exists and was not saved unhashed
    assert admin.pin is not None
    assert admin.pin != 11111

def test_verify_password (create_admin_user) :
    admin = create_admin_user

    assert admin.verify_password('password') is True
    assert admin.verify_password('invalid') is False

def test_check_pin (create_admin_user) :
    # created with pin = 11111
    admin = create_admin_user

    assert admin.check_pin(11111) is True
    assert admin.check_pin(00000) is False

def test_is_password_expired (flask_app, create_admin_user) :
    # created with password = 'password'
    admin = create_admin_user
    # asserting that password is not expired upon creation
    assert admin.is_password_expired() is False

    # manually expiring password, asserting that method now returns True
    admin.password_expiration = datetime.now(timezone.utc) - timedelta(days = 1)
    assert admin.is_password_expired() is True


def test_renew_password (create_admin_user) :
    # created with password = 'password'
    admin = create_admin_user

    # should still be expired from previous test
    assert admin.is_password_expired() is True

    # change pin from 'password' to 'newpassword'
    admin.renew_password('password', 'newpassword')

    # checking that password expiration was updated
    assert admin.is_password_expired() is False

    # checking that password was actually changed
    assert admin.verify_password('newpassword') is True
    assert admin.verify_password('password') is False


# tests for admin controllers
def test_signup (flask_app) :

    response = flask_app.post('/api/admin/signup/',
        headers = { 'Authorization': f'Bearer mock_uid' },
        json = { 
            'name': 'Test',
            'email': 'admintest@gmail.com',
            'password': 'password',
            'pin': 12345,
        }
    )

    assert response.status_code == 201

    new_admin = Admin.query.filter_by(email = 'admintest@gmail.com').first()
    assert new_admin is not None
    assert new_admin.employee_id == response.json['employeeId']


@pytest.mark.parametrize('valid_id, valid_password, valid_pin, expired_password', [
    (True, True, True, False), # valid login
    (True, True, True, True), # need to update password
    (True, False, None, None), # invalid credentials
    (True, True, False, None), # invalid credentials
    (False, None, None, None), # invalid credentials
])
def test_login (flask_app, valid_id, valid_password, valid_pin, expired_password) :
    admin = Admin.query.filter_by(name = 'Test').first()

    employee_id = admin.employee_id if valid_id else 00000000
    pin = 12345 if valid_pin else 00000
    password = 'password' if valid_password else 'invalid'

    
    if expired_password :
        # setting pin expiration to day before
        admin.password_expiration = datetime.now(timezone.utc) - timedelta(days = 1)
        db.session.commit()
        db.session.refresh(admin)

    with patch('backend.api.utils.token.generate_jwt') as mock_generate_jwt :
        mock_generate_jwt.side_effect = ['access_token_mock', 'refresh_token_mock']

        response = flask_app.post('/api/admin/login/',
            json = {
                'employeeId': employee_id,
                'password': password,
                'pin': pin
            },
        )

        if valid_id and valid_password and valid_pin and not expired_password :
            assert response.status_code == 200
            assert all(
                any(
                    token in cookie for cookie in response.headers.getlist('Set-Cookie')
                ) for token in ('access_token=', 'refresh_token='
            ))
        elif valid_id and valid_password and valid_pin and expired_password :
            assert response.status_code == 403
            assert response.json['message'] == 'Password is expired, please renew password'
        else :
            assert response.status_code == 401
            assert response.json['error'] == 'Invalid credientials'


@pytest.mark.parametrize('valid_email, valid_id, valid_password, valid_pin', [
    (False, None, None, None), # invalid credentials
    (True, True, True, False), # invalid credentials
    (True, True, False, None), # invalid credentials
    (True, False, None, None), # invalid credentials
    (True, True, True, True), # successful update
])
def test_update_password (flask_app, valid_email, valid_id, valid_password, valid_pin) :
    admin = Admin.query.filter_by(name = 'Test').first()

    email = admin.email if valid_email else 'invalid@email.com'
    employee_id = admin.employee_id if valid_id else 00000000
    pin = 12345 if valid_pin else 00000
    old_password = 'password' if valid_password else 'invalid'

    new_password = 'newPassword'

    with patch('backend.api.utils.token.generate_jwt') as mock_generate_jwt :
        mock_generate_jwt.side_effect = ['access_token_mock', 'refresh_token_mock']
        response = flask_app.post('/api/admin/update-password/',
            # need to pass values as str to mimic http request body
            json = {
                'email': email,
                'employeeId': str(employee_id),
                'oldPassword': old_password,
                'password': new_password,
                'pin': pin
            }
        )

    if valid_id and valid_password and valid_pin :
        assert response.status_code == 200
        assert all(
            any(
                token in cookie for cookie in response.headers.getlist('Set-Cookie')
            ) for token in ('access_token=', 'refresh_token='
        ))

        db.session.refresh(admin)
        assert admin.verify_password(new_password) is True

    else :
        assert response.status_code == 401
        assert response.json['error'] == 'Invalid credientials'

@pytest.mark.parametrize('valid_code', [True, False])
def test_validate_employer_code (flask_app, valid_code) :
    code = os.getenv('EMPLOYER_CODE') if valid_code else 00000000
    response = flask_app.post('/api/admin/validate-code/',
        json = {
            'code': code
        }
    )

    assert response.status_code == (200 if valid_code else 400)