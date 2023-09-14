from flask import Blueprint, jsonify, request, current_app
from flask_bcrypt import Bcrypt
import datetime


from ..app import db
from ..models import User, Role

bcrypt = Bcrypt()

user_bp = Blueprint('user', __name__)

@user_bp.route('/signup', methods = ['POST'])
def signup () :
    try :
        data = request.get_json()

        user_data = {
                key: data.get(key) for key in ['name', 'email', 'password', 'billing_address', 'shipping_address']
        }

        existing_user = User.query.filter_by(email = user_data['email']).first()
        if existing_user :
            return jsonify({
                'message': 'Email address is already in use'
            }), 400
        
        # hash password with bcrypt
        hashed_password = bcrypt.generate_password_hash(user_data['password']).decode('utf-8')
        user_data['password'] = hashed_password

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

    

