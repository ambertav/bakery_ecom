from flask import Blueprint, jsonify, request, current_app, make_response
import redis
import jwt

from ...database import db
from ..utils.redis_service import cache_token, is_token_blacklisted
from ..utils.token import generate_jwt, decode_jwt, get_time_until_jwt_expire
from ..utils.set_auth_cookies import set_tokens_in_cookies
from ..decorators import token_required
from ..models import User, Admin

from .cart_item import create_item

user_bp = Blueprint('user', __name__)


@user_bp.route('/signup', methods = ['POST'])
def signup () :
    '''
    Handle user signup by creating a new user, processing the shopping cart, creating access token, and setting cookies.

    Returns :
        Response : JSON response with a success message and any cart errors if applicable, or an error message in case of failure.
    '''
    try :
        data = request.json

        if data.get('password') != data.get('confirm_password') :
            return jsonify({
                'error': 'Passwords do not match'
            }), 400

        user_data = {
            'name': data.get('name'),
            'email': data.get('email'),
            'password': data.get('password'),
        }

        new_user = User(**user_data)

        db.session.add(new_user) 
        db.session.commit()

        shopping_cart = request.json.get('localStorageCart')

        if shopping_cart :
            cartError = process_shopping_cart(shopping_cart, new_user) # formats local storage cart to create cart item, returns errors if any
        else :
            cartError = None

        access_token = generate_jwt(new_user.id, 'user', 15)
        refresh_token = generate_jwt(new_user.id, 'user', 7 * 24 * 60)

        response = set_tokens_in_cookies(response, access_token, refresh_token)

        return response
    
    except Exception as error :
        current_app.logger.error(f'Error registering user: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500
    

@user_bp.route('/login', methods = ['POST'])
def login () :
    '''
    Handle user login by authenticating the user and processing the shopping cart.

    Returns :
        Response : JSON response with a success message and any cart errors if applicable, or an error message in case of failure.
    '''
    try :
        data = request.json

        user = User.query.filter_by(email = data.get('email')).first()
    
        if not user or not user.verify_password(data.get('password')) :
            return jsonify({
                'message': 'Invalid credientials'
            }), 400
        
        shopping_cart = request.json.get('localStorageCart')

        if shopping_cart :
            cartError = process_shopping_cart(shopping_cart, user) # formats local storage cart to create cart item, returns errors if any
        else :
            cartError = None
            
        access_token = generate_jwt(user.id, 'user', 15)
        refresh_token = generate_jwt(user.id, 'user', 7 * 24 * 60)

        response = make_response(
            jsonify({
                'message': 'User logged in successfully',
                'cartError': cartError
            }), 200
        )

        response = set_tokens_in_cookies(response, access_token, refresh_token)

        return response
        
    except Exception as error :
        current_app.logger.error(f'Error logging user in: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500

@user_bp.route('/logout', methods = ['GET'])
def logout () :
    response = make_response(jsonify({
        'message': 'Successfully logged out'
    }), 200)

    try :
        refresh_token = request.cookies.get('refresh_token')
        if not refresh_token :
            raise ValueError('No refresh token found')

        # add buffer time of 5 minutes        
        ttl = int(get_time_until_jwt_expire(refresh_token)) + 300

        if ttl > 0 :
            cache_token(refresh_token, ttl)
    
    except redis.RedisError as re :
        current_app.logger.error(f'Redis error: {str(re)}')
        response = make_response(jsonify({
            'error': 'Redis error'
        }), 500)

    except Exception as error :
        current_app.logger.error(f'Error logging user out: {str(error)}')
        response = make_response(jsonify({
            'error': 'Internal server error'
        }), 500)

    finally :
        # delete cookies
        response = set_tokens_in_cookies(response, '', '')

        return response

    
@user_bp.route('/info', methods = ['GET'])
@token_required
def get_user_info () :
    '''
    Retrieve user or admin status and information.

    Returns :
        Response : JSON response with the user's / admin's name and admin status, or an error message in case of failure.
    '''
    try :
        # authenticate for both user and admin
        user = request.user
        admin = request.admin

        # determining user's/admin's name and admin status
        name = admin.name if admin else user.name
        is_admin = bool(admin)
        role = admin.role.value.lower() if admin else 'client'

        # return info
        return jsonify({
            'user': {
                'name': name,
                'isAdmin': is_admin,
                'role': role,
            }
        }), 200
    
    except Exception as error :
        current_app.logger.error(f'Error retrieving user info: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500
    
@user_bp.route('/refresh', methods = ['GET'])
def refresh_authentication_tokens () :
    try :
        token = request.cookies.get('refresh_token')

        if not token :
            return jsonify({
                'error': 'Authentication failed'
            }), 401
        
        if is_token_blacklisted(token) :
            raise jwt.InvalidTokenError
        
        payload = decode_jwt(token)

        id = payload.get('sub')
        role =  payload.get('role')

        if not id or not role :
            return jsonify({
                'error': 'Authentication failed'
            }), 401
        
        user, admin = None, None
        
        if role == 'user' :
            user = User.query.get(id)
        elif role == 'admin' :
            admin = Admin.query.get(id)
        
        if not user and not admin :
            return jsonify({
                'error': 'Forbidden',
            }), 403
        
        ttl = int(get_time_until_jwt_expire(token)) + 300

        if ttl > 0 :
            cache_token(token, ttl)
        
        access_token = generate_jwt(id, payload.get('role'), 15)
        refresh_token = generate_jwt(id, payload.get('role'), 7 * 24 * 60)

        response = make_response(
            jsonify({
                'message': 'Tokens refreshed successfully',
            }), 200
        )

        response = set_tokens_in_cookies(response, access_token, refresh_token)

        return response

    except jwt.InvalidTokenError :
        return jsonify({
            'error': 'Invalid token'
        }), 401
    
    except Exception as error :
        current_app.logger.error(f'Error refreshing tokens: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500


def process_shopping_cart(shopping_cart, user) :
    '''
    Process the shopping cart by creating cart items for each product.

    Intended for use for when user creates cart_items in local storage when unauthenticated,
    to then create associated cart_items when the user autenticates (both via signing up,
    or logging in).

    Args :
        shopping_cart (list) : list of cart items from local storage.
        user (User) : user object.

    Returns :
        str : a string of errors, if any, encountered while processing the cart items.
    '''
    errors = []
    if shopping_cart :
        for item in shopping_cart :
            data = {
                'id': item.get('product').get('id'),
                'qty': item.get('quantity'),
                'portion': item.get('portion').get('id'),
            }
            response = create_item(data, user) # creates cart item for each item in shopping cart
            if not response['success'] :
                errors.append(f"Error adding item with ID {data['id']} to the cart") # catches errors per item

    cartError = ', '.join(errors) if errors else ''
    return cartError # returns errors, if any