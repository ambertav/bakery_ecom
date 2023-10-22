from flask import Blueprint, jsonify, request, current_app, make_response
from flask_cors import cross_origin
import datetime


from ..app import db, auth
from ..auth import auth_user
from ..models import User, Role, AddressType

from .cart_item import cart_item_bp
from .order import order_bp

user_bp = Blueprint('user', __name__)

user_bp.register_blueprint(cart_item_bp, url_prefix = '/cart')
user_bp.register_blueprint(order_bp, url_prefix = '/order')

@user_bp.route('/signup', methods = ['POST'])
@cross_origin()
def signup () :
    try :
        # retrieve token
        token = request.headers['Authorization'].replace('Bearer ', '')
        # decode to retrieve uid
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token['uid']

        user_data = {}
        # assign all fields for user creation
        user_data['name'] = request.data
        user_data['firebase_uid'] = uid
        user_data['billing_address'] = None
        user_data['shipping_address'] = None
        user_data['role'] = Role.CLIENT
        user_data['created_at'] = datetime.datetime.utcnow()

        new_user = User(**user_data)

        db.session.add(new_user)
        db.session.commit()

        return jsonify({
            'message': 'User registered successfully'
        }), 201
    
    except Exception as error :
        current_app.logger.error(f'Error registering user: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500
    

@user_bp.route('/login', methods = ['POST'])
@cross_origin()
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
            return jsonify({
                'message': 'User logged in successfully'
            }), 200
        
    except Exception as error :
        current_app.logger.error(f'Error logging user in: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500
    

@user_bp.route('/get-address', methods = ['GET'])
def get_addresses () :
    try :
        # retrieve token and auth user
        token = request.headers['Authorization'].replace('Bearer ', '')
        user = auth_user(token)

        addresses = user.addresses.all()

        # if no addresses, set billing and shipping to None
        if not addresses :
            billing_list = None
            shipping_list = None
        else : 
            billing_list = [address.as_dict() for address in addresses if address.type == AddressType.BILLING or address.type == AddressType.BOTH]
            shipping_list = [address.as_dict() for address in addresses if address.type == AddressType.SHIPPING or address.type == AddressType.BOTH]

        return jsonify({
            'billAddress': billing_list,
            'shipAddress': shipping_list
        }), 200

    except Exception as error :
        current_app.logger.error(f'Error retrieving user addresses: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500