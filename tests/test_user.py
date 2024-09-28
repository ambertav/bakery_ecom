import pytest
from unittest.mock import patch

from ..api.models import User

def test_hash_password (create_client_user) :
    # created with password = 'password'
    user = create_client_user

    assert user.password != 'password'
    assert isinstance(user.password, bytes)

def test_verify_password (create_client_user) :
    user = create_client_user

    assert user.verify_password('password') is True
    assert user.verify_password('invalid') is False

def test_signup (flask_app) :
    with patch('backend.api.utils.token.generate_jwt') as mock_generate_jwt, \
        patch('backend.api.blueprints.user.process_shopping_cart') as mock_process_cart :

        mock_generate_jwt.side_effect = ['access_token_mock', 'refresh_token_mock']
        mock_process_cart.return_value = None

        response = flask_app.post('/api/user/signup', 
            json = { 
                'name': 'Test',
                'email': 'email@gmail.com',
                'password': 'password',
                'confirm_password': 'password',
                'localStorageCart': ['item1', 'item2']
            })

        assert response.status_code == 201
        assert all(
            any(
                token in cookie for cookie in response.headers.getlist('Set-Cookie')
            ) for token in ('access_token=', 'refresh_token='
        ))

    new_user = User.query.filter_by(name = 'Test').first()
    assert new_user is not None

# mock firebase, user login
def test_login (flask_app) :
    created_user = User.query.filter_by(name = 'Test').first()

    with patch('backend.api.utils.token.generate_jwt') as mock_generate_jwt :
        mock_generate_jwt.side_effect = ['access_token_mock', 'refresh_token_mock']
        response = flask_app.post('/api/user/login',
            json = {
                'email': 'email@gmail.com',
                'password': 'password',
                'localStorageCart': None
            },
        )

        assert response.status_code == 200
        assert all(
            any(
                token in cookie for cookie in response.headers.getlist('Set-Cookie')
            ) for token in ('access_token=', 'refresh_token='
        ))

def test_get_user_info (flask_app) :
    user = User.query.filter_by(name = 'Test').first()

    with patch('flask.request.cookies.get') as mock_get_cookie, \
        patch('backend.api.utils.token.decode_jwt') as mock_decode_jwt :

        mock_get_cookie.return_value = 'valid_access_token'
        mock_decode_jwt.return_value = {
            'name': user.name,
            'isAdmin': False,
            'sub': user.id
        }

        response = flask_app.get('/api/user/info')

    assert response.status_code == 200
    assert response.json['user']['name'] ==  user.name
    assert response.json['user']['isAdmin'] == False

@pytest.mark.parametrize('refresh_token, is_blacklisted, decode_jwt_return, expected_status, expected_message', [
    ('valid_refresh_token', False, {'sub': 1, 'role': 'user'}, 200, 'Tokens refreshed successfully'),  # Successful case
    (None, False, None, 401, 'Invalid token'),  # No token case
    ('valid_refresh_token', True, {'sub': 1, 'role': 'user'}, 401, 'Invalid token'),  # Blacklisted token case
    ('valid_refresh_token', False, None, 401, 'Invalid token'),  # Invalid token case
    ('valid_refresh_token', False, {'sub': 9999, 'role': 'user'}, 401, 'Invalid token')  # User not found case
])
def test_refresh_authentication_tokens (flask_app, create_client_user, refresh_token, is_blacklisted, decode_jwt_return, expected_status, expected_message) :
    user = create_client_user

    with patch('flask.request.cookies.get', return_value = refresh_token), \
        patch('backend.api.utils.redis_service.is_token_blacklisted', return_value = is_blacklisted), \
        patch('backend.api.utils.token.decode_jwt', return_value = decode_jwt_return), \
        patch('backend.api.models.User.query.get', return_value = user if decode_jwt_return and decode_jwt_return['sub'] == user.id else None), \
        patch('backend.api.utils.token.generate_jwt') as mock_generate_jwt :

        mock_generate_jwt.side_effect = ['new_access_token', 'new_refresh_token'] if expected_status == 200 else [None, None]

        response = flask_app.get('/api/user/refresh')

        assert response.status_code == expected_status
        assert response.json['error'] == expected_message if expected_status != 200 else response.json['message'] == expected_message
        
def test_logout (flask_app) :
    refresh_token = 'valid_refresh_token'

    with patch('flask.request.cookies.get', return_value = refresh_token), \
        patch('backend.api.utils.token.get_time_until_jwt_expire', return_value = 100), \
        patch('backend.api.utils.redis_service.cache_token') as mock_cache_token, \
        patch('backend.api.utils.set_auth_cookies.set_tokens_in_cookies') as mock_set_cookies :
        
        response = flask_app.get('/api/user/logout')

        assert response.status_code == 200
        assert response.json['message'] == 'Successfully logged out'