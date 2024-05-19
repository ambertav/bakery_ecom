from flask import Blueprint, jsonify, request, current_app
import stripe
import os
import json
import datetime

from decimal import Decimal

from ...database import db
from ..utils.auth import auth_user, auth_admin
from ..models.models import User, Address, Cart_Item, Portion, Order, Order_Status, Pay_Status, Deliver_Method, Task

webhook_secret = os.getenv('WEBHOOK_SECRET')

order_bp = Blueprint('order', __name__)

@order_bp.route('/', methods = ['GET'])
def order_history_index () :
    try :
        # retrieve token and auth user
        user = auth_user(request)

        if user is None :
            return jsonify({
                'error': 'Authentication failed'
            }), 401
                
        page = request.args.get('page', 1, type = int)
        
        # check if recent query parameter is included and set to true
        is_recent = request.args.get('recent', '').lower() == 'true'

        base_query =  Order.query.filter_by(user_id = user.id).order_by(Order.date.desc())
        
        if is_recent :
            # filter by user, sort by date, only take most recent 3
            orders = base_query.limit(3).all()
            order_history = [ order.as_dict() for order in orders ]

            return jsonify({
                'orders': order_history,
            }), 200
        
        else :
            orders = base_query.paginate(page = page, per_page = 10)
            order_history = [ order.as_dict() for order in orders.items ]
            
            return jsonify({
                'orders': order_history,
                'totalPages': orders.pages,
                'currentPage': page
            }), 200


    except Exception as error :
        current_app.logger.error(f'Error fetching orders: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500
    

@order_bp.route('/<int:id>', methods = ['GET'])
def show_order (id) :
    try :
        user = auth_user(request)

        if user is None:
            return jsonify({
                'error': 'Authentication failed'
            }), 401
        
        order = Order.query.filter_by(id = id, user_id = user.id).first()

        if order :
            order_detail = order.as_dict()
            cart_items = order.cart_items
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


@order_bp.route('/fulfillment/pending/', methods = ['GET'])
def order_fulfillment_get_pending () :
    # user auth done in get_fulfillment_orders_by_status function
    page = request.args.get('page', 1, type = int)
    delivery_method = request.args.get('delivery-method')
    search = request.args.get('search')
    return get_fulfillment_orders_by_status('PENDING', page, delivery_method, search)
    

@order_bp.route('/fulfillment/in-progress/', methods = ['GET'])
def order_fulfillment_get_in_progress () :
    # user auth done in get_fulfillment_orders_by_status function
    page = request.args.get('page', 1, type = int)
    delivery_method = request.args.get('delivery-method')
    search = request.args.get('search')
    return get_fulfillment_orders_by_status('IN_PROGRESS', page, delivery_method, search)


def get_fulfillment_orders_by_status (status, page, delivery_method, search) :
    try :
        # authentication and authorization check
        admin = auth_admin(request)
        if admin is None :
            return jsonify({
                'error': 'Authentication failed'
            }), 401


        # if there is a search param, search by the specific id and return
        if search :
            # retrieve order
            order = Order.query.filter_by(id = search).first()
            if order :
                # format order and corresponding cart_items
                order_data = [
                    { **order.as_dict(), 'items': [ item.as_dict() for item in order.cart_items ] }
                ]

                return jsonify({
                    'orders': order_data, 
                    'totalPages': 1, 
                    'currentPage': 1
                }), 200
            
            else:
                return jsonify({
                    'orders': [], 
                    'message': 'Order not found'
                }), 200


        else :
            # retrieve orders based on status and page passed into function

            # initialize base query
            base_query = Order.query.filter_by(status = Order_Status[status])

            if delivery_method :
                # add delivery method filter if present
                base_query = base_query.filter_by(delivery_method = Deliver_Method[delivery_method.upper()])


            # makes query, orders by date, paginates
            orders = (
                base_query
                    .order_by(Order.date.asc())
                    .paginate(page = page, per_page = 50)
            )

            if orders.items :
                # formats orders and corresponding cart_items
                order_history = [
                    { **order.as_dict(), 'items': [ item.as_dict() for item in order.cart_items ] }
                    for order in orders.items
                ]

                return jsonify({
                    'orders': order_history,
                    'totalPages': orders.pages,
                    'currentPage': page
                }), 200
            
            else :
                return jsonify({
                    'orders': [],
                    'message': 'No orders found'
                }), 200


    except Exception as error :
        current_app.logger.error(f'Error retrieving order fulfillment: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500

@order_bp.route('/fulfillment/set-in-progress/', methods = ['PUT'])
def start_orders_and_create_admin_tasks () :
    try :
        # authentication and authorization check
        admin = auth_admin(request)
        if admin is None :
            return jsonify({
                'error': 'Authentication failed'
            }), 401
        
        data = request.get_json()

        try :
            # start a nested transaction
            with db.session.begin_nested() :
                # extract the order ids
                for order_id in data :
                    # convert id to int, retrieve orders
                    order = Order.query.get(int(order_id))
                    if order :
                        # set order status to in progress
                        order.status = Order_Status.IN_PROGRESS
                        # create a new task, associating order and admin user
                        task = Task(
                            admin_id = admin.id,
                            order_id = order_id,
                            created_at = datetime.datetime.now(),
                            completed_at = None
                        )
                        db.session.add(task)
                    else :
                        raise ValueError(f'Order with id {order_id} was not found')

            # commit nested transaction
            db.session.commit()

        except Exception as error :
            # rollback entire transaction if error
            db.session.rollback()
            raise 

        return jsonify({
            'message': 'Successfully started orders and created tasks'
        }), 200

    except Exception as error :
        current_app.logger.error(f'Error batch starting orders: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500

@order_bp.route('/fulfillment/<int:id>/set-pending/', methods = ['PUT'])
def return_order_to_pending (id) :
    try :
        # authentication and authorization check
        admin = auth_admin(request)
        if admin is None :
            return jsonify({
                'error': 'Authentication failed'
            }), 401
        
        # verify that user owns task
        task = Task.query.filter_by(order_id = id, admin_id = admin)
        if not task :
            return jsonify({
                'error': 'Forbidden'
            }), 403
        
        # return order to pending
        order = Order.query.get(id)
        order.status = Order_Status.PENDING

        # delete task
        task.delete()

        db.session.commit()

        return jsonify({
            'message': 'Order was successfully returned to pending and task was unassigned'
        }), 200


    except Exception as error :
        current_app.logger.error(f'Error returning order to pending status: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500

@order_bp.route('/fulfillment/<int:id>/set-complete/', methods = ['PUT'])
def complete_order_fulfillment (id) :
    pass

@order_bp.route('/create-checkout-session', methods = ['POST'])
def create_checkout_session() :
    # retrieve token and auth user
    user = auth_user(request)

    if user is None :
        return jsonify({
            'error': 'Authentication failed'
        }), 401
    
    cart = request.json.get('cart')
    method = request.json.get('method')
    billing = request.json.get('billing')
    shipping = request.json.get('shipping')
            
    # create necessary user addresses from delivery form input
    if billing == shipping:
        address_id = handle_address(billing, user)
    else:
        handle_address(billing, user)
        address_id = handle_address(shipping, user)

    # dynamically create line_items for stripe checkout session from cart information
    line_items = []
    cart_ids = []
    for item in cart :
        line_item = {
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': item['name'],
                    'description': item['portion'],
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
                'user': user.id, # pass in user id for order creation
                'address_id': address_id # only passing in shipping address to associate with order
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
            method = session['metadata'].get('method')
            user_id = session['metadata'].get('user')
            address_id = session['metadata'].get('address_id')

            # create instance of order
            new_order = create_order(address_id, user_id, method)

            user = User.query.filter_by(id = user_id).first()

            # associate stripe's customer id with user in database
            if user and not user.stripe_customer_id :
                user.stripe_customer_id = session['customer']

            try :
                # finalize order with payment info from stripe
                new_order.stripe_payment_id = session['payment_intent']
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

def create_order (address, user, method) :
    try :
        # find the cart items and calculate total
        items_to_associate = Cart_Item.query.filter_by(user_id = user, ordered = False).all()
        total = sum(item.price * item.quantity for item in items_to_associate)

        # create instance of order and associate with user
        new_order = Order(
            user_id = user,
            date = datetime.datetime.now(),
            total_price = total,
            status = Order_Status.PENDING,
            stripe_payment_id = None,
            delivery_method = Deliver_Method[method.upper()],
            payment_status = Pay_Status.PENDING,
            shipping_address_id = address,
        )

        db.session.add(new_order)

        # commit and refresh to get access to new_order.id
        db.session.commit()
        db.session.refresh(new_order)

        # loop through items and update ordered boolean, associate to new order
        for item in items_to_associate :
            item.ordered = True
            item.order_id = new_order.id

            if item.portion == Portion.SLICE :
                # if portion is slice, deduct by 1/8, or 0.125, * quantity of slices
                item.product.stock -= Decimal(0.125) * Decimal(item.quantity)
            elif item.portion == Portion.MINI :
                # if portion is mini, deduct by 1/2, or 0.5, * quantity of minis
                item.product.stock -= Decimal(0.5) * Decimal(item.quantity)
            else :
                item.product.stock -= Decimal(item.quantity)

        db.session.commit()

        # use class method to create and associate task for new order
        new_order.create_associated_task()

        return new_order
        
    except Exception as error :
        current_app.logger.error(f'Error creating order: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500
    
def handle_address (address, user) :
    try :
        # search for address
        existing_address = Address.query.filter_by(
            first_name = address['firstName'],
            last_name = address['lastName'],
            street = address['street'],
            city = address['city'],
            state = address['state'],
            zip = address['zip'],
            user_id = user.id,
        ).one_or_none()

        # handles cases where existing address was previously either billing or shipping, but was then selected for both
        if existing_address :
            return existing_address.id # returns id only to pass into order creation

        # create address if necessary
        if existing_address is None :
            new_address =  Address(
                first_name = address['firstName'],
                last_name = address['lastName'],
                street = address['street'],
                city = address['city'],
                state = address['state'],
                zip = address['zip'],
                user_id = user.id,
                default = False,
            )

            db.session.add(new_address)
            db.session.commit()

            return new_address.id # returns id only to pass into order creation

    except Exception as error :
        current_app.logger.error(f'Error handling address: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500



