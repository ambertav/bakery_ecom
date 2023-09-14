from flask import Blueprint, jsonify, request, current_app

from ..app import db
from ..models import User, Product, Cart_Item

cart_item_bp = Blueprint('cart_item', __name__)

@cart_item_bp.route('/add', methods = ['POST'])
def add_to_cart () :
    try :
        data = request.get_json()

        product = Product.query.get(data.get('product_id'))

        if not product :
            return jsonify({
                'error': 'Product not found'
            })

        # get user id, NEEDS AUTH
        user_id = 1

        new_item = Cart_Item(user_id = user_id, product_id = product.id, quantity = data.get('quantity'))

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