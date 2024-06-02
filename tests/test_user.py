from unittest.mock import patch

from ..api.models.models import User


# mock firebase, user sign up
def test_signup (flask_app) :
    with patch('firebase_admin.auth.verify_id_token') as mock_verify_id_token :
        mock_verify_id_token.return_value = { 'uid': 'mock_uid' }
        input_data = { 'name': 'Test' }

        response = flask_app.post('/api/user/signup',
            headers = { 'Authorization': f'Bearer mock_uid' },
            json = input_data,
        )

    assert response.status_code == 201
    assert response.json['message'] == 'User registered successfully'

    new_user = User.query.filter_by(name = input_data['name']).first()
    assert new_user is not None
    assert new_user.firebase_uid == 'mock_uid'

# mock firebase, user login
def test_login (flask_app, mock_firebase) :
    created_user = User.query.filter_by(name = 'Test').first()

    with mock_firebase(created_user.firebase_uid) :
        response = flask_app.post('/api/user/login',
            headers = { 'Authorization': f'Bearer {created_user.firebase_uid}' },
            json = {
                'name': '',
                'localStorageCart': None
            },
        )

    assert response.status_code == 200
    assert response.json['message'] == 'User logged in successfully'

def test_get_user_info (flask_app, create_client_user, mock_firebase) :
    user, test_uid = create_client_user

    with mock_firebase(test_uid) :
        response = flask_app.get('/api/user/info',
            headers = { 'Authorization': f'Bearer {test_uid}' }
        )

    # asserting that name and admin status is correctly sent
    assert response.status_code == 200
    assert response.json['name'] ==  user.name
    assert response.json['isAdmin'] == False
