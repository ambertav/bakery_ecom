from flask import Blueprint, jsonify, request, current_app
import stripe
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

@order_bp.route('/create-checkout-session', methods=['POST'])
def create_checkout_session() :
    cart = request.json.get('cart')

    # dynamically create line_items for stripe checkout session from cart information
    line_items = []
    for item in cart :
        line_item = {
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': item['name'],
                },
                'unit_amount': int(float(item['price']) * 100), # convert price to cents
            },
            'quantity': int(item['quantity']),
        }
        line_items.append(line_item)

    try :
        # create stripe checkout session
        session = stripe.checkout.Session.create(
            line_items = line_items,
            mode = 'payment',
            success_url='http://localhost:4242/success',
            cancel_url='http://localhost:3000/cart',
        )

        return jsonify({
            'checkout_url': session.url
        })
    
    except Exception as error :
        current_app.logger.error(f'Error: {str(error)}')
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
def show_order (id) :
    try :
        order = Order.query.get(id)

        if order :
            order_detail = order.as_dict()
            cart_items = order.items
            cart_item_details = [item.as_dict() for item in cart_items]
            order_detail['items'] = cart_item_details

            return jsonify({
                'order': order_detail
            }), 200
        else :
            return jsonify({
                'error': 'Order not found'
            }), 404

    except Exception as error :
        current_app.logger.error(f'Error fetching order details: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500