from flask import Blueprint, jsonify, request, current_app
import stripe, json
from datetime import datetime

from ..app import db, webhook_secret
from ..auth import auth_user
from ..models import User, Address, Cart_Item, Order, Order_Status, Pay_Status, Ship_Method


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
    method = request.json.get('method')

    billing = request.json.get('billing')
    shipping = request.json.get('shipping')

    # retrieve token and auth user
    token = request.headers['Authorization'].replace('Bearer ', '')
    user = auth_user(token)
    if user is None :
        return jsonify({
            'error': 'Authentication failed'
        }), 401
            
    # create necessary user addresses from delivery form input
    if billing == shipping:
        handle_address(billing, user, address_type = 'BOTH')
    else:
        handle_address(billing, user, address_type = 'BILLING')
        handle_address(shipping, user, address_type = 'SHIPPING')

    # dynamically create line_items for stripe checkout session from cart information
    line_items = []
    cart_ids = []
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
        cart_ids.append(item['id'])

    try :
        # create stripe checkout session
        session = stripe.checkout.Session.create(
            line_items = line_items,
            mode = 'payment',
            success_url = 'http://localhost:3000/cart/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url = 'http://localhost:3000/cart',
            metadata = {
                'cart': str(cart_ids), # pass in string of cart ids for order creation
                'method': method, # pass in delivery method from delivery form input
                'user': user.id # pass in user id for order creation
            }
        )

        return jsonify({
            'checkout_url': session.url
        })
    
    except Exception as error :
        current_app.logger.error(f'Error: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500
    
@order_bp.route('/stripe-webhook', methods = ['POST'])    
def handle_stripe_webhook () :
    event = None
    payload = request.data

    try :
        event = json.loads(payload)
    except json.decoder.JSONDecodeError as error :
        current_app.logger.error(f'Webhook error while parsing basic request: {str(error)}')
        return jsonify(
            success = False
        )
    
    if webhook_secret :
        sig_header = request.headers.get('Stripe-Signature')
        try :
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except stripe.error.SignatureVerificationError as error:
            current_app.logger.error(f'Webhook signature verification failed: {str(error)}')
            return jsonify(
                success = False
            )
        

        if event and event['type'] == 'checkout.session.completed' :
            session = event['data']['object']
            cart = session.metadata.get('cart')
            method = session.metadata.get('method')
            user_id = session.metadata.get('user')

            # create instance of order
            new_order = create_order(cart, user_id, method)

            user = User.query.filter_by(id = user_id).first()

            # associate stripe's customer id with user in database
            if user and not user.stripe_customer_id :
                user.stripe_customer_id = session.customer

            try :
                # finalize order with payment info from stripe
                new_order.stripe_payment_id = session.payment_intent
                new_order.status =  Order_Status.PROCESSING
                new_order.payment_status =  Pay_Status.COMPLETED

                db.session.commit()

            except Exception as error :
                current_app.logger.error(f'Error finalizing order: {str(error)}')
                return jsonify({
                    'error': 'Internal server error'
                }), 500

        else :
            print('Unhandled event type {}'.format(event['type']))
    
    return jsonify(
        success = True
    )

def create_order (cart, user, method) :
    try :
        # find the cart items and calculate total
        items_to_associate = Cart_Item.query.filter_by(user_id = user, ordered = False).all()
        total = sum(item.product.price * item.quantity for item in items_to_associate)

        # create instance of order and associate with user
        new_order = Order(
            user_id = user,
            date = datetime.now(),
            total_price = total,
            status = 'PENDING',
            stripe_payment_id = None,
            shipping_method = Ship_Method.STANDARD,
            payment_method = None,
            payment_status = Pay_Status.PENDING
        )

        db.session.add(new_order)

        # associate cart items with order, and update cart_items to ordered
        new_order.items.extend(items_to_associate)
        for item in items_to_associate :
            item.ordered = True

        db.session.commit()
        
        return new_order
        
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
    
def handle_address (address, user, address_type) :
    try :
        # search for address
        existing_address = Address.query.filter_by(
            first_name = address['firstName'],
            last_name = address['lastName'],
            street = address['address'],
            city = address['city'],
            state = address['state'],
            zip_code = address['zip'],
            user_id = user.id,
            type = address_type,
        ).one_or_none()
    
        # create address if necessary
        if existing_address is None :
            new_address =  Address(
                first_name = address['firstName'],
                last_name = address['lastName'],
                street = address['address'],
                city = address['city'],
                state = address['state'],
                zip_code = address['zip'],
                user_id = user.id,
                type = address_type,
            )

            db.session.add(new_address)
            db.session.commit()

    except Exception as error :
        current_app.logger.error(f'Error handling address: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500








