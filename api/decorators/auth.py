from functools import wraps
from flask import request, jsonify
import jwt
import os

from ..models import User, Admin
from ..utils.token import decode_jwt

secret_key = os.getenv('SECRET_KEY')

def token_required (f) :
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.cookies.get('access_token')

        if not token:
            return jsonify({
                'error': 'Authentication required'
            }), 401
        
        user, admin = None, None

        try:
            payload = decode_jwt(token)

            id = payload.get('sub')
            role = payload.get('role')

            if not id or not role :
                return jsonify({
                    'error': 'Authentication failed'
                }), 401
            
            if role == 'user' :
                user = User.query.get(id)
            elif role == 'admin' :
                admin = Admin.query.get(id)
            
            request.user = user
            request.admin = admin

            if user is None and admin is None :
                return jsonify({
                    'error': 'User or Admin not found'
                }), 401

        except jwt.ExpiredSignatureError:
            return jsonify({
                'error': 'Token expired'
            }), 401
        
        except jwt.InvalidTokenError:
            return jsonify({
                'error': 'Invalid token'
            }), 401


        return f(*args, **kwargs)
    
    return decorated_function
