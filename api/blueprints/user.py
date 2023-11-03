from flask import Blueprint, jsonify, request, current_app
import datetime


from ...app import db, auth
from ..models.models import User, Role

from .cart_item import create_item

user_bp = Blueprint('user', __name__)

@user_bp.route('/signup', methods = ['POST'])
def signup () :
    try :
        # retrieve token
        token = request.headers['Authorization'].replace('Bearer ', '')
        # decode to retrieve uid
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token['uid']

        user_data = {
            'name': request.json.get('name'),
            'firebase_uid': uid,
            'stripe_customer_id': None,
            'billing_address': None,
            'shipping_address': None,
            'role': Role.CLIENT,
            'created_at': datetime.datetime.utcnow()
        }

        new_user = User(**user_data)

        db.session.add(new_user) 
        db.session.commit()

        shopping_cart = request.json.get('localStorageCart')
        cartError = process_shopping_cart(shopping_cart, new_user) # formats local storage cart to create cart item, returns errors if any

        return jsonify({
            'message': 'User registered successfully',
            'cartError': cartError
        }), 201
    
    except Exception as error :
        current_app.logger.error(f'Error registering user: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500
    

@user_bp.route('/login', methods = ['POST'])
def login () :
    try :
        # retrieve token
        token = request.headers['Authorization'].replace('Bearer ', '')
        # decode to retrieve uid
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token['uid']

        user = User.query.filter_by(firebase_uid = uid).first()

        if not user :
            return jsonify({
                'message': 'User not found'
            }), 404
        
        else :
            shopping_cart = request.json.get('localStorageCart')
            cartError = process_shopping_cart(shopping_cart, user) # formats local storage cart to create cart item, returns errors if any
                
            return jsonify({
                'message': 'User logged in successfully',
                'cartError': cartError
            }), 200
        
    except Exception as error :
        current_app.logger.error(f'Error logging user in: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500
    

def process_shopping_cart(shopping_cart, user) :
    errors = []
    if shopping_cart :
        for item in shopping_cart :
            data = {
                'id': item.get('productId'),
                'qty': item.get('quantity')
            }
            response = create_item(data, user) # creates cart item for each item in shopping cart
            if not response['success'] :
                errors.append(f"Error adding item with ID {data['id']} to the cart") # catches errors per item

    cartError = ', '.join(errors) if errors else ''
    return cartError # returns errors, if any