import pytest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
import os

from ..database import db
from ..api.models.models import Admin

# mock firebase, user sign up
def test_signup (flask_app) :
    with patch('firebase_admin.auth.verify_id_token') as mock_verify_id_token :
        mock_verify_id_token.return_value = { 'uid': 'mock_uid' }
        input_data = { 
            'name': 'Test',
            'pin': 12345,
        }

        response = flask_app.post('/api/admin/signup/',
            headers = { 'Authorization': f'Bearer mock_uid' },
            json = input_data,
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
def test_login (flask_app, valid_id, valid_pin, expired_pin) :
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

    with patch('firebase_admin.auth.verify_id_token') as mock_verify_id_token :
        mock_verify_id_token.return_value = { 'uid': admin.firebase_uid }

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
def test_update_pin (flask_app, valid_id, valid_pin) :
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

    with patch('firebase_admin.auth.verify_id_token') as mock_verify_id_token :
        mock_verify_id_token.return_value = { 'uid': admin.firebase_uid }

        response = flask_app.post('/api/admin/update-pin/',
            headers = { 'Authorization': f'Bearer {admin.firebase_uid}' }, 
            # need to pass values as str to mimic http request body
            json = {
                'employeeId': str(employee_id),
                'oldPin': str(old_pin),
                'pin': '67890'
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