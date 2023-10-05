from flask import Blueprint, jsonify, request, current_app

from ..app import db, auth
from ..models import User, Product, Cart_Item

cart_item_bp = Blueprint('cart_item', __name__)

# index
@cart_item_bp.route('/', methods = ['GET'])
def view_cart() :
    try :
        cart_items = Cart_Item.query.filter_by(user_id = 1).all() # needs user auth

        if cart_items :
            shopping_cart = [
                item.as_dict() for item in cart_items
            ]
        else :
            return jsonify({
                'error': 'Shopping cart not found'
            }), 404
        
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
        cart_item = Cart_Item.query.get(id)

        if not cart_item :
            return jsonify({
                'error': 'Item not found in cart'
            }), 404
        
        db.session.delete(cart_item)
        db.session.commit()
        return jsonify({
            'message': ' Item deleted from cart successfully'
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
        data = request.get_json()
        new_quantity = data.get('quantity')

        cart_item = Cart_Item.query.get(id)
        
        if not cart_item :
            return jsonify({
                'error': 'Item not found in cart'
            }), 404
        else :
            if new_quantity == 0 :
                db.session.delete(cart_item)
            else :
                cart_item.quantity = new_quantity

            db.session.commit()
            return jsonify({
                'message': 'Item quantity updated successfully'
            }), 200
            
    except Exception as error :
        current_app.logger.error(f'Error updating item in cart: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500

# create
@cart_item_bp.route('/add', methods = ['POST'])
def add_to_cart () :
    try :
        data = request.get_json()

        # retrieve token
        token = request.headers['Authorization'].replace('Bearer ', '')

        product = Product.query.get(data.get('id'))

        if not product :
            return jsonify({
                'error': 'Product not found'
            }), 404
        

        # retrieve and authenticate user
        try :
            user = auth_user(token)
        except Exception as error :
            current_app.logger.error(f'Error authenticating user: {str(error)}')
            return jsonify({
                'error': 'Internal server error'
            }), 500
        
        
        new_item = Cart_Item(user_id = user.id, product_id = product.id, quantity = 1, ordered = False)

        db.session.add(new_item)
        db.session.commit()
        
        return jsonify({
            'message': 'Item added successfully'
        }), 201

    except Exception as error :
        current_app.logger.error(f'Error adding to cart: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500
    

def auth_user (token) :
    try :
        # decode to retrieve uid
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token['uid']

        user = User.query.filter_by(firebase_uid = uid).first()
        if not user :
            return None
        else :
            return user
    except Exception as error :
        current_app.logger.error(f'Error authenticating user: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500