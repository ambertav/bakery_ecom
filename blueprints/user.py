from flask import Blueprint, jsonify, request, current_app, make_response
from flask_cors import cross_origin
import datetime


from ..app import db, auth
from ..auth import auth_user
from ..models import User, Role

from .cart_item import cart_item_bp, add_to_cart
from .order import order_bp
from .address import address_bp

user_bp = Blueprint('user', __name__)

user_bp.register_blueprint(cart_item_bp, url_prefix = '/cart')
user_bp.register_blueprint(order_bp, url_prefix = '/order')
user_bp.register_blueprint(address_bp, url_prefix = '/address')

@user_bp.route('/signup', methods = ['POST'])
def signup () :
    try :
        # retrieve token
        token = request.headers['Authorization'].replace('Bearer ', '')
        # decode to retrieve uid
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token['uid']

        user_data = {}
        # assign all fields for user creation
        user_data['name'] = request.json.get('name')
        user_data['firebase_uid'] = uid
        user_data['stripe_customer_id'] = None
        user_data['billing_address'] = None
        user_data['shipping_address'] = None
        user_data['role'] = Role.CLIENT
        user_data['created_at'] = datetime.datetime.utcnow()

        new_user = User(**user_data)

        db.session.add(new_user) 
        db.session.commit()

        shopping_cart = request.json.get('localStorageCart')
        if shopping_cart :
            for item in shopping_cart :
                data = {
                    'id': item.get('productId'),
                    'qty': item.get('quantity')
                }
                response = add_to_cart(data = data, user = new_user)

        return jsonify({
            'message': 'User registered successfully'
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
            if shopping_cart :
                for item in shopping_cart :
                    data = {
                        'id': item.get('productId'),
                        'qty': item.get('quantity')
                    }
                    response = add_to_cart(data = data, user = user)

            return jsonify({
                'message': 'User logged in successfully'
            }), 200
        
    except Exception as error :
        current_app.logger.error(f'Error logging user in: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500