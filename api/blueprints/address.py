from flask import Blueprint, jsonify, request, current_app

from ...database import db
from ..decorators import token_required
from ..models import Address

address_bp = Blueprint('address', __name__)

@address_bp.route('/', methods = ['GET'])
@token_required
def get_addresses () :
    '''
    Retrieves the addressed associated with the authenticated user.

    If a 'default' query parameter is provided and set to 'true', only the address matched default = True is returned.
    Otherwise, all addresses are returned with the default address at the top.

    Returns :
        Response : JSON response containing a list of address dictionaries or an error message
    '''
    try :
        user = request.user

        is_default = request.args.get('default', '').lower() == 'true'

        if is_default:
            # retrieve the default address for the user
            default_address = user.addresses.filter_by(default = True).first()
            address_history = default_address.as_dict() if default_address else []
        else:
            # retrieve all addresses for the user
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
@token_required
def update_default (id) :
    '''
    Updates the default address for the authenticated user.

    Sets the address with the given ID as the default.
    If there is already a default address, it is updated to no longer be the default.

    Args :
        id (int) : ID of the address to set as the default.

    Returns :
        Response : JSON response indicating success or an error message.
    '''
    try :
        user = request.user

        set_default = user.addresses.filter_by(id = id).first()

        if set_default : # if the address to set as default was found
            current_default =  user.addresses.filter_by(default = True).first() # find current default
            if current_default :
                current_default.toggle_default() # set current default as false
    
            set_default.toggle_default() # set new default
            db.session.commit()

            return jsonify({
                'message': 'Default address updated successfully'
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
    
@address_bp.route('/<int:id>/delete', methods = ['DELETE'])
@token_required
def delete (id) :
    '''
    Deletes an address for authenticated user.

    Removes the address with the given ID from the user's addresses.

    Args :
        id (int) : ID of the address to delete.

    Returns :
        Response : JSON response indicating success or an error message.
    '''
    try : 
        user = request.user
        
        deleted_address = user.addresses.filter_by(id = id).first()

        if deleted_address :     
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
        if 'violates not-null constraint' in f'{str(error)}' :
            db.session.rollback()
            return jsonify({
                'error': 'Violates not null constraint',
            }), 400
        
        return jsonify({
            'error': 'Internal server error',
        }), 500