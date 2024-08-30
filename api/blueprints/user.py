from flask import Blueprint, jsonify, request, current_app, make_response

from ...database import db
from ..utils.token import generate_jwt, decode_jwt
from ..utils.auth import auth_user, auth_admin
from ..models import User

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

        token = generate_jwt(new_user.id)

        response = make_response(jsonify({
            'message': 'User registered successfully',
            'cartError': cartError
        }), 201)

        response.set_cookie(
            'access_token',
            value = token,
            httponly = 'true',
            max_age = 60 * 60 * 24 * 7,
            samesite = 'None',
            secure = 'false'
        )

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
        user = auth_user(request)

        if not user :
            return jsonify({
                'message': 'User not found'
            }), 404
        
        else :
            shopping_cart = request.json.get('localStorageCart')
            if shopping_cart :
                cartError = process_shopping_cart(shopping_cart, user) # formats local storage cart to create cart item, returns errors if any
            else :
                cartError = None
                
            return jsonify({
                'message': 'User logged in successfully',
                'cartError': cartError
            }), 200
        
    except Exception as error :
        current_app.logger.error(f'Error logging user in: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500
    
@user_bp.route('/info', methods = ['GET'])
def get_user_info () :
    '''
    Retrieve user or admin status and information.

    Returns :
        Response : JSON response with the user's / admin's name and admin status, or an error message in case of failure.
    '''
    try :
        # authenticate for both user and admin
        user = auth_user(request)
        admin = auth_admin(request)

        # if neither user nor admin, return 404
        if not user and not admin :
            return jsonify({
                'message': 'User not found'
            }), 404

        # determining user's/admin's name and admin status
        name = admin.name if admin else user.name
        is_admin = bool(admin)

        # return info
        return jsonify({
            'name': name, 
            'isAdmin': is_admin
        }), 200
    
    except Exception as error :
        current_app.logger.error(f'Error retrieving user info: {str(error)}')
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