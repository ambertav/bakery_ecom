import jwt
import os
from datetime import datetime, timezone, timedelta

secret_key = os.getenv('SECRET_KEY')

def generate_jwt (user_id) :
    expiration = datetime.now(timezone.utc) + timedelta(days = 7)
    payload = {
        'sub': user_id,
        'exp': expiration
    }

    return jwt.encode(payload, secret_key, algorithm = 'HS256')

def decode_jwt (token) :
    try :
        decoded_payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return decoded_payload.get('sub')
    
    except jwt.InvalidTokenError :
        return 'Invalid token'
    