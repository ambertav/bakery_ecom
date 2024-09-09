from flask import Blueprint, jsonify, request, current_app
from sqlalchemy.orm import joinedload
import stripe
import os
import json
import datetime

from ...database import db
from ..decorators import token_required
from ..models import Address, Cart_Item, Order
from ..models.order import Order_Status, Pay_Status, Deliver_Method

webhook_secret = os.getenv('WEBHOOK_SECRET')

order_bp = Blueprint('order', __name__)

@order_bp.route('/', methods = ['GET'])
@token_required
def order_history_index () :
    '''
    Retrieves paginated list of orders for authenticated user.

    Optionally, if 'recent' parameter is set to 'true', filters to show the 3 most recents orders

    Returns :
        Response : JSON response containing list of order dictionaries, total pages, and the current page, or error message.
    '''
    try :
        user = request.user
                
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
@token_required
def show_order (id) :
    '''
    Retrieves details for a specific order by ID for the authenticated user.
    
    Returns :
        Response : JSON response with order details or an error message if there an error occurred or if order is not found.
    '''
    try :
        user = request.user
        
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
@token_required
def order_fulfillment_get_pending () :
    '''
    Retrieves a paginated list of pending orders for admins.

    Optionally filters by delivery method and search term if 'delivery-method' or 'search' parameters are present.
    
    Returns :
        Response : JSON response with pending orders or error message.
    '''
    admin = request.admin
    page = request.args.get('page', 1, type = int)
    delivery_method = request.args.get('delivery-method')
    search = request.args.get('search')
    return get_fulfillment_orders_by_status(admin,'PENDING', page, delivery_method, search)
    

@order_bp.route('/fulfillment/in-progress/', methods = ['GET'])
@token_required
def order_fulfillment_get_in_progress () :
    '''
    Retrieves a paginated list of orders in progress for admins.

    Optionally filters by delivery method and search term if 'delivery-method' or 'search' parameters are present.
    
    Returns :
        Response : JSON response with in-progress orders or error message.
    '''
    admin = request.admin
    page = request.args.get('page', 1, type = int)
    delivery_method = request.args.get('delivery-method')
    search = request.args.get('search')
    return get_fulfillment_orders_by_status(admin, 'IN_PROGRESS', page, delivery_method, search)


def get_fulfillment_orders_by_status (admin, status, page, delivery_method, search) :
    '''
    Retrieves a paginated list of orders based on their fulfillment status for admins.

    Optionally filters by delivery method and search term if present.
    
    Args :
        status (str) : fulfillment status of the orders to retrieve.
        page (int) : page number for pagination.
        delivery_method (str) : optional filter for delivery method.
        search (str) : optional search term to filter by order ID.
    
    Returns :
        Response : JSON response with list of order dictionaries, total pages, and the current page, or error message.
    '''
    try :
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
@token_required
def start_orders_and_assign_admin_tasks () :
    '''
    Starts one or multiple orders and assigns associated tasks to the authenticated admin.

    Request Body :
        data (list) : list of string order IDs of the orders to update
    
    Returns :
        Response : JSON response indicating success or error message.
    '''
    try :
        admin = request.admin

        try :
            # extract the order ids
            for order_id in request.get_json() :
                # convert id to int, retrieve orders
                order = Order.query.get(int(order_id))
                if order :
                    order.status_start(admin.id)
                else :
                    raise ValueError(f'Order with id {order_id} was not found')

            # commit the transaction
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
@token_required
def return_order_to_pending (id) :
    '''
    Returns a specific order to pending status and unassigns the associated admin.

    If the requesting admin does not match the associated admin, a PermissionError is raised.
    If the order is not in-progress at the time of the request or if the order is not
    found, a ValueError is raised.
    
    Returns :
        Response : JSON response indicating success or error message.
    '''
    try :
        admin = request.admin
        
        # query for order
        order = Order.query.get(id)

        # if found and current status is pending
            # return order to pending
        if order :
            try :
                order.status_undo(admin.id)
                db.session.commit()

                return jsonify({
                    'message': 'Order was successfully returned to pending and admin was unassigned'
                }), 200
            
            except Exception as error :
                return handle_status_update_error(error)

        else :
            return handle_status_update_error(ValueError('Order not found'))

    except Exception as error :
        current_app.logger.error(f'Error returning order to pending status: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500

@order_bp.route('/fulfillment/<int:id>/set-complete/', methods = ['PUT'])
@token_required
def complete_order_fulfillment (id) :
    '''
    Marks a specific order to as completed and finalizes the associated task.

    If the requesting admin does not match the associated admin, a PermissionError is raised.
    If the order is not in-progress at the time of the request or if the order is not
    found, a ValueError is raised.
    
    Returns :
        Response : JSON response indicating success or error message.
    '''
    try :
        admin = request.admin
        
        # query for order
        order = Order.query.get(id)

        # if found and current status is pending
            # set order to completed
        if order :
            try :
                order.status_complete(admin.id)
                db.session.commit()

                return jsonify({
                    'message': 'Order and associated task were successfully completed'
                }), 200

            except Exception as error :
                return handle_status_update_error(error)

        else :
            return handle_status_update_error(ValueError('Order not found'))

    except Exception as error :
        current_app.logger.error(f'Error completing order and task: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500

@order_bp.route('/create-checkout-session', methods = ['POST'])
@token_required
def create_checkout_session() :
    '''
    Creates a Stripe checkout session for the authenticated user based on cart information.

    Request Body :
        cart (Cart_Item) : cart_items the user is checking out for.
        method (str) : delivery method for the order.
        billing (Address) : billing address for the order.
        shipping (Address) : shipping address for the order.
    
    Returns :
        Response : JSON response with the Stripe checkout URL or error message.
    '''
    user = request.user
    
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
                    'name': item['product']['name'],
                    'description': item['portion']['size']
                },
                'unit_amount': int(float(item['portion']['price']) * 100), # convert price to cents
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
    '''
    Handles Stripe webhook events to finalize orders upon successful checkout.
    
    Returns:
        Response : JSON response indicating success or failure.
    '''
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
                new_order.finalize_order_payment(session['id'], session['payment_intent'])
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
    '''
    Creates a new order and associates it with the given user, address, and delivery method.
    
    Args :
        address (int) : ID of the address for shipping.
        user (int) : ID of the user placing the order.
        method (str) : delivery method for the order.
    
    Returns :
        Order instance if successful, otherwise an error response.
    '''
    try :
        # find the cart items and calculate total
        items_to_associate = Cart_Item.query.filter_by(user_id = user, ordered = False).all()
        total = sum(item.price for item in items_to_associate)

        # create instance of order and associate with user
        new_order = Order(
            user_id = user,
            date = datetime.datetime.now(),
            total_price = total,
            status = Order_Status.PENDING,
            delivery_method = Deliver_Method[method.upper()],
            payment_status = Pay_Status.PENDING,
            shipping_address_id = address,
        )

        db.session.add(new_order)

        # commit and refresh to get access to new_order.id
        db.session.commit()
        db.session.refresh(new_order)

        new_order.associate_items(items_to_associate)

        for item in items_to_associate :
            item.portion.update_stock(item.portion.stock - item.quantity)
        
        db.session.commit()

        new_order.create_associated_task()

        return new_order
        
    except Exception as error :
        current_app.logger.error(f'Error creating order: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500
    
def handle_address (address, user) :
    '''
    Handles address creation or retrieval for the authenticated user to be used for order checkout.

    Attempts to retrieve a matching address from user's associated addresses, and creates a new address
    instance if no matching existing address is found.
    
    Args :
        address (dict) : address details.
        user (int) : ID of the user.
    
    Returns:
        Address ID if successful, otherwise an error response.
    '''
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


def handle_status_update_error (error) :
    '''
     Handles errors occurring during status updates of orders.
    
    Args :
        error (Exception) : the exception that occurred.
    
    Returns :
        Response : JSON response with error details and appropriate HTTP status code.
    '''
    # 400 code if order status isn't currently IN_PROGRESS
    # 403 code if unable to match to assigned admin
    # 500 code else

    db.session.rollback()
    error_message = str(error)

    if isinstance(error, ValueError) :
        status_code = 400
    elif isinstance(error, PermissionError) :
        status_code = 403
    else :
        status_code = 500
        error_message = 'Internal server error'

    return jsonify({
        'error': error_message
    }), status_code
