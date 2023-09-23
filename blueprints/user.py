from flask import Blueprint, jsonify, request, current_app
from flask_cors import cross_origin
import datetime


from ..app import db, auth
from ..models import User, Role

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

        print(request.data)

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