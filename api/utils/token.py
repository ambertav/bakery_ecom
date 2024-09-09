import jwt
import os
from datetime import datetime, timezone, timedelta

secret_key = os.getenv('SECRET_KEY')

def generate_jwt (user_id, role, expiration) :
    '''
    Generates a jwt token for both access and refresh tokens.

    Args :
        user_id (str) : user or admin id.
        role (str) : either user or admin
        expiration (int) : token expiration in minutes from the current time

    Returns :
        str : JWT token with the user ID as the subject (sub) and the expiration time (exp) set.
    '''

    payload = {
        'sub': user_id,
        'role': role,
        'exp': datetime.now(timezone.utc) + timedelta(minutes = expiration)
    }

    return jwt.encode(payload, secret_key, algorithm = 'HS256')

def decode_jwt (token) :
    '''
    Decodes a JWT token to extract the payload, including user ID (sub) and expiration time (exp).

    Args :
        token (str) : JWT token to decode.

    Returns :
        dict : Decoded JWT payload containing 'sub' (user or admin ID), 'role' (either user or admin), and 'exp' (expiration).
    
    Raises :
        Exception : If token decoding fails or the token is invalid.
    '''
    try :
        return jwt.decode(token, secret_key, algorithms=['HS256'])
    
    except Exception as error :
        raise error
    
def get_time_until_jwt_expire (token) :
    '''
    Extracts expiration time from JWT token payload and calculates the seconds from now to that expiration time.

    Args :
        token (str) : JWT token to decode.

    Returns :
        float : number of seconds from current time until the JWT token expires.
    
    Raises :
        Exception : If token decoding fails or the token is invalid.

    '''
    try :
        expiration = jwt.decode(token, secret_key, algorithms=['HS256']).get('exp')
        expiration_time = datetime.fromtimestamp(expiration, tz = timezone.utc)
        current_time = datetime.now(timezone.utc)
        
        return (expiration_time - current_time).total_seconds()
    
    except Exception as error :
        raise error

    