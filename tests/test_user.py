from unittest.mock import patch

from ..api.models import User


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
    assert isinstance(new_user.password, bytes)

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
