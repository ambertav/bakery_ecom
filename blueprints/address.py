from flask import Blueprint, jsonify, request, current_app
from flask_cors import cross_origin

from ..app import db
from ..auth import auth_user
from ..models import Address

address_bp = Blueprint('address', __name__)

@address_bp.route('/', methods = ['GET'])
def get_addresses () :
    try :
        # retrieve token and auth user
        token = request.headers['Authorization'].replace('Bearer ', '')
        user = auth_user(token)
        if user is None:
            return jsonify({
                'error': 'Authentication failed'
            }), 401

        is_default = request.args.get('default', '').lower() == 'true'

        if is_default:
            # Retrieve the default address for the user
            default_address = user.addresses.filter_by(default = True).first()
        else:
            # Retrieve all addresses for the user
            addresses = user.addresses.all()

        if is_default and default_address :
            address_history = default_address.as_dict()
        elif not is_default and addresses :
            address_history = [ address.as_dict() for address in addresses ]
        else :
            address_history = []

        return jsonify({
            'addresses': address_history
        }), 200

    except Exception as error :
        current_app.logger.error(f'Error retrieving user addresses: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500