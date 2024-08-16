from flask import Blueprint, jsonify, request, current_app

from ...database import db
from ..utils.auth import auth_user

from ..models import Product, Cart_Item

cart_item_bp = Blueprint('cart_item', __name__)

# index
@cart_item_bp.route('/', methods = ['GET'])
def view_cart() :
    try :
        user = auth_user(request)

        if user is None:
            return jsonify({
                'error': 'Authentication failed'
            }), 401

        cart_items = Cart_Item.query.filter_by(user_id = user.id, ordered = False).all()

        if cart_items :
            shopping_cart = [
                item.as_dict() for item in cart_items
            ]
        else :
            shopping_cart = None
        
        return jsonify({
            'shopping_cart': shopping_cart
        }), 200
        
    except Exception as error :
        current_app.logger.error(f'Error fetching shopping cart: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500

# delete
@cart_item_bp.route('/<int:id>/delete', methods = ['DELETE'])
def delete_cart_item (id) :
    try :
        user = auth_user(request)

        if user is None:
            return jsonify({
                'error': 'Authentication failed'
            }), 401

        cart_item = Cart_Item.query.filter_by(id = id, user_id = user.id).first()

        if not cart_item :
            return jsonify({
                'error': 'Item not found in cart'
            }), 404
        
        db.session.delete(cart_item)
        db.session.commit()
        return jsonify({
            'message': 'Item deleted from cart successfully'
        }), 200

    except Exception as error :
        current_app.logger.error(f'Error deleting item from cart: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500

# update
@cart_item_bp.route('/<int:id>/update', methods = ['PUT'])
def update_quantity (id) :
    try :
        user = auth_user(request)

        if user is None:
            return jsonify({
                'error': 'Authentication failed'
            }), 401
        
        data = request.get_json()

        cart_item = Cart_Item.query.filter_by(id = id, user_id = user.id).first()
        
        if not cart_item :
            return jsonify({
                'error': 'Item not found in cart'
            }), 404
        
        try :
            result = cart_item.update_quantity(data.get('newQty'))
            if result == 'delete' :
                db.session.delete(cart_item)

            db.session.commit()

            return jsonify({
                'message': 'Item quantity updated successfully'
            }), 200
            
        except ValueError as ve :
            db.session.rollback()
            return jsonify({
                'error': str(ve)
            }), 400
    
    except Exception as error :
        current_app.logger.error(f'Error updating item in cart: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500

# create
@cart_item_bp.route('/add', methods = ['POST'])
def add_to_cart () :
    try :
        # retrieve token
        user = auth_user(request)

        if user is None:
            return jsonify({
                'error': 'Authentication failed'
            }), 401
        
        data = request.get_json()

        response = create_item(data, user) # adds to database, returns with boolean and message

        if response['success'] == True:
            return jsonify({
                'message': response['message']
            }), 201
        else :
            return jsonify({
                'error': 'Product not found'
            }), 404

    except Exception as error :
        current_app.logger.error(f'Error adding to cart: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500
    
def create_item (data, user) : 
    try :
        # ensure valid product
        product = Product.query.get(int(data.get('id')))

        if not product :
            return {
                'success': False,
                'message': 'Product not found'
            }

        # search users existing cart for an unordered item with matching product_id and portion size
        existing_item = Cart_Item.query.filter_by(user_id = user.id, product_id = product.id, portion_id = data.get('portion'), ordered = False).first()

        if existing_item :
            try :
                qty = int(data.get('qty'))
                # update quantity of existing item instead of creating new cart item
                result = existing_item.update_quantity(existing_item.quantity + qty) 
                if result == 'delete' :
                    db.session.delete(existing_item)

                success = True
            except ValueError :
                return {
                    'success': False,
                    'message': 'Invalid quantity format'
                }
        else :
            # otherwise, create item with product id and inputted quantity and portion
            new_item = Cart_Item(user_id = user.id, product_id = product.id, portion_id = data.get('portion'), quantity = data.get('qty'), ordered = False, order_id = None)
            db.session.add(new_item)
            success = True

        db.session.commit()

        return {
            'success': success,
            'message': 'Item added successfully'
        }
    
    except Exception as error :
        current_app.logger.error(f'Error adding to cart: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500