from flask import Blueprint, jsonify, request, current_app
from datetime import datetime

from ..app import db
from ..models import User, Cart_Item, Order, Order_Status, Pay_Status

order_bp = Blueprint('order', __name__)


@order_bp.route('/', methods = ['GET'])
def order_history_index () :
    try :
        orders = Order.query.filter_by(user_id = 1).all()

        if orders :
            order_history = [
                order.as_dict() for order in orders
            ]
        else :
            return jsonify({
                'error': 'Orders not found'
            }), 404
        
        return jsonify({
            'order_history': order_history
        }), 200


    except Exception as error :
        current_app.logger.error(f'Error fetching orders: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500

@order_bp.route('/create', methods = ['POST'])
def create_order () :
    try :
        data = request.get_json()

        user_id = 1
        cart_items = Cart_Item.query.filter_by(user_id = 1).all()

        if not cart_items :
            return jsonify({
                'message': 'No items in the cart. Cannot create order.'
            }), 400
        
        total = sum(item.product.price * item.quantity for item in cart_items)

        new_order = Order(
            user_id = user_id,
            date = datetime.now(),
            total_price = total,
            status = Order_Status.PENDING,
            shipping_method = data.get('shipping_method'),
            payment_method = data.get('payment_method'),
            payment_status = Pay_Status.PENDING
        )

        for cart_item in cart_items :
            new_order.items.append(cart_item)
            cart_item.ordered = True

        db.session.add(new_order)
        db.session.commit()

        return jsonify({
            'message': 'Order created successfully.'
        }), 200
    except Exception as error :
        current_app.logger.error(f'Error creating order: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500


@order_bp.route('/<int:id>', methods = ['GET'])
def show_order () :
    pass