from flask import Blueprint, jsonify, request, current_app
from flask_cors import cross_origin

from ...app import db
from ..utils.auth import auth_user
from ..models.models import Address

address_bp = Blueprint('address', __name__)

@address_bp.route('/', methods = ['GET'])
def get_addresses () :
    try :
        user = auth_user(request)

        if user is None:
            return jsonify({
                'error': 'Authentication failed'
            }), 401

        is_default = request.args.get('default', '').lower() == 'true'

        if is_default:
            # Retrieve the default address for the user
            default_address = user.addresses.filter_by(default = True).first()
            address_history = default_address.as_dict() if default_address else []
        else:
            # Retrieve all addresses for the user
            addresses = user.addresses.order_by(Address.default.desc()).all() # sends default at the top
            address_history = [ address.as_dict() for address in addresses ] if addresses else []

        return jsonify({
            'addresses': address_history
        }), 200

    except Exception as error :
        current_app.logger.error(f'Error retrieving user addresses: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500
    
@address_bp.route('/default/<int:id>', methods = ['PUT'])
def update_default (id) :
    try :
        # retrieve token and auth user
        user = auth_user(request)

        if user is None:
            return jsonify({
                'error': 'Authentication failed'
            }), 401
        
        set_default = user.addresses.filter_by(id = id).first()

        if set_default : # if the address to set as default was found
            current_default =  user.addresses.filter_by(default = True).first() # find current default
            if current_default :
                current_default.default = False # set current default as false
    
            set_default.default = True # set new default
            db.session.commit()

            return jsonify({
                'message': 'Default address updated successfully'
            }), 200
        
        else :
            return jsonify({
                'message': 'Address not found'
            }), 404

    except Exception as error :
        current_app.logger.error(f'Error updating default address: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500
    
@address_bp.route('/<int:id>/delete', methods = ['DELETE'])
def delete (id) :
    try : 
        # retrieve token and auth user
        user = auth_user(request)

        if user is None:
            return jsonify({
                'error': 'Authentication failed'
            }), 401
        
        deleted_address = user.addresses.filter_by(id = id).first()

        if deleted_address :
            if deleted_address.default == True : # if the address to delete is designated as default...
                next_address = user.addresses.filter(Address.id != id).first() # finds next available address to set as default
                if next_address:
                    next_address.default = True
                    
            db.session.delete(deleted_address)
            db.session.commit()

            return jsonify({
                'message': 'Address deleted successfully'
            }), 200

        else :
            return jsonify({
                'error': 'Address not found'
            }), 404  
    
    except Exception as error :
        current_app.logger.error(f'Error updating default address: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500