from flask import Blueprint, jsonify, request, current_app
from sqlalchemy.orm import joinedload
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
            return jsonify({
                'order': order.as_dict()
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
                order_data = [ { **order.as_dict() } ]

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

            # join task with order
            base_query = base_query.options(joinedload(Order.task))

            # makes query, orders by date, paginates
            orders = (
                base_query
                    .order_by(Order.date.asc())
                    .paginate(page = page, per_page = 50)
            )

            if orders.items :
                # formats orders and corresponding cart_items and tasks
                order_history = [
                    {  **order.as_dict(), 'task': order.task.as_dict() if order.task else None }
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
def start_orders_and_assign_admin_tasks () :
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
                        # query for task and assign admin
                        task = Task.query.filter_by(order_id = order.id).first()
                        task.assign_admin(admin.id)
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
        
        # query for order
        order = Order.query.get(id)

        # if found and current status is pending
            # return order to pending
        if order :
            if order.status == Order_Status.IN_PROGRESS :
                order.status = Order_Status.PENDING

                # query for and verify that requesting admin is assigned to the task
                task = Task.query.filter_by(order_id = id, admin_id = admin.id).first()
                if not task :
                    return jsonify({
                        'error': 'Forbidden'
                    }), 403

                # unassign admin from task
                task.unassign_admin()

                db.session.commit()

                return jsonify({
                    'message': 'Order was successfully returned to pending and admin was unassigned'
                }), 200
            
            # 400 code if order status isn't currently IN_PROGRESS
            else :
                return jsonify({
                    'error': 'Order status could not be updated'
                }), 400

        else :
            return jsonify({
                'error': 'Order not found'
            }), 404

    except Exception as error :
        current_app.logger.error(f'Error returning order to pending status: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500

@order_bp.route('/fulfillment/<int:id>/set-complete/', methods = ['PUT'])
def complete_order_fulfillment (id) :
    try :
        # authentication and authorization check
        admin = auth_admin(request)
        if admin is None :
            return jsonify({
                'error': 'Authentication failed'
            }), 401
        
        # query for order
        order = Order.query.get(id)

        # if found and current status is pending
            # set order to completed
        if order :
            if order.status == Order_Status.IN_PROGRESS :
                order.status = Order_Status.COMPLETED

                # query for and verify that requesting admin is assigned to the task
                task = Task.query.filter_by(order_id = id, admin_id = admin.id).first()
                if not task :
                    return jsonify({
                        'error': 'Forbidden'
                    }), 403

                # complete task
                task.complete()

                db.session.commit()

                return jsonify({
                    'message': 'Order and associated task were successfully completed'
                }), 200
            
            # 400 code if order status isn't currently IN_PROGRESS
            else :
                return jsonify({
                    'error': 'Order status could not be updated'
                }), 400

        else :
            return jsonify({
                'error': 'Order not found'
            }), 404


    except Exception as error :
        current_app.logger.error(f'Error completing order and task: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500

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

            try :
                # finalize order with session and payment info from stripe
                new_order.stripe_session_id = session['id']
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

        new_order.associate_items(items_to_associate)
        new_order.create_associated_task()

        # commit and refresh to get access to new_order.id
        db.session.commit()
        db.session.refresh(new_order)

        return new_order
        
    except Exception as error :
        current_app.logger.error(f'Error creating order: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500
    
def handle_address (address, user) :
    try :
        
        # process the address input so that capitals and extra space are removed
            # use this cleaned up input to query database
        processed_address = { key: value.strip() if isinstance(value, str) else value for (key, value) in address.items() }

        # search for address
        existing_address = Address.query.filter(
            Address.first_name.ilike(processed_address['firstName']),
            Address.last_name.ilike(processed_address['lastName']),
            Address.street.ilike(processed_address['street']),
            Address.city.ilike(processed_address['city']),
            Address.state.ilike(processed_address['state']),
            Address.zip.ilike(processed_address['zip']),
            Address.user_id == user.id
        ).one_or_none()

        # handles cases where existing address was previously either billing or shipping, but was then selected for both
        if existing_address :
            return existing_address.id # returns id only to pass into order creation

        # create address if necessary
        if existing_address is None :
            new_address =  Address(
                first_name = processed_address['firstName'],
                last_name = processed_address['lastName'],
                street = processed_address['street'],
                city = processed_address['city'],
                state = processed_address['state'],
                zip = processed_address['zip'],
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



