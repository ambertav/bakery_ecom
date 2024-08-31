import jwt

from ..models import User, Admin
from .token import decode_jwt


def auth_user (request) :
    '''
    Authenticate a user based on the access token in the request cookies.

    Args :
        request (flask.Request) : request object containing the cookies.

    Returns :
        User or None: authenticated user object if successful, otherwise None.
    '''
    return authenticate(User, request)


def auth_admin (request) :
    '''
    Authenticate an admin based on the access token in the request cookies.

    Args :
        request (flask.Request) : request object containing the cookies.

    Returns :
        Admin or None: authenticated admin object if successful, otherwise None.
    '''
    return authenticate(Admin, request)


def authenticate (model, request) :
    '''
    Authenticate a user or admin based on the access token in the request cookies.

    Args:
        model (Type[User or Admin]) : model class (User or Admin) to query for authentication.
        request (flask.Request) : request object containing the cookies.

    Returns :
        User or Admin or None: authenticated user or admin object if successful, otherwise None.

    Raises :
        ValueError : If the token has expired or is invalid.
    '''
    try :
        token = request.cookies.get('access_token')

        if not token :
            return None
        
        id = decode_jwt(token)

        user_or_admin = model.query.get(id)

        return user_or_admin if user_or_admin else None
        
    except jwt.ExpiredSignatureError :
        raise ValueError('Token has expired')
    
    except jwt.InvalidTokenError :
        raise ValueError('Invalid token')