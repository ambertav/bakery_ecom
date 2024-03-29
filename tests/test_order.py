import pytest
import unittest
import json
import datetime

from unittest.mock import patch, MagicMock

from ..database import db
from ..config import config
from ..api.models.models import Order, Order_Status, Deliver_Method, Pay_Status, User, Address, Cart_Item, Portion, Product, Category

@pytest.fixture(scope = 'module')
def seed_database (flask_app, create_client_user) :
    try:
        user, test_uid = create_client_user

        product = Product(
            name = 'Product 1',
            description = 'Description 1',
            category = Category.CAKE,
            image = 'https://example.com/image.jpg',
            price = 10.00,
            stock = 100
        )
        db.session.add(product)
        db.session.commit()

        address = Address(
            first_name = 'Jane',
            last_name = 'Doe',
            street = '123 Main St',
            city = 'Anytown',
            state = 'NY',
            zip = '10001',
            default = False,
            user_id = user.id,
        )
        db.session.add(address)
        db.session.commit()

        cart_item = Cart_Item(
            user_id = user.id,
            product_id = product.id,
            quantity = 1,
            portion = Portion.WHOLE,
            ordered = False,
            order_id = None
        )
        db.session.add(cart_item)
        db.session.commit()

        # returns cart item and address for use throughout module tests
        yield cart_item, address

    finally:
        db.session.rollback()
        db.session.close()


# testing case of existing address or new address submitted
@pytest.mark.parametrize('to_create_address', (True, False))
def test_create_checkout_session (flask_app, create_client_user, seed_database, to_create_address) :
    user, test_uid = create_client_user
    cart_item, address = seed_database

    if to_create_address :
        # new address, in camelCase format due to frontend
        shipping = {
            'firstName': 'Jane',
            'lastName': 'Doe',
            'street': '123 First Ave',
            'city': 'New York',
            'state': 'NY',
            'zip': '10001',
        }

    else :
        # if not case of new address, use existing
        shipping = address.as_dict()

    with patch('firebase_admin.auth.verify_id_token', MagicMock(return_value = { 'uid': test_uid })) :
        response = flask_app.post('/api/order/create-checkout-session',
            headers = { 'Authorization': f'Bearer {test_uid}' },
            json = {
                'cart': [cart_item.as_dict()],
                'method': 'STANDARD',
                'billing': address.as_dict(),
                'shipping': shipping
            },
        )

    assert response.status_code == 200
    assert response.json['checkout_url'] is not None

    if to_create_address :
        # if applicable, asserting that new address was created with input
        new_address = Address.query.filter_by(user_id = user.id, street = shipping['street']).first()
        assert new_address is not None


def test_handle_stripe_webhook (flask_app, create_client_user, seed_database) :
    # create user and get cart item and address
    user, test_uid = create_client_user
    cart_item, address = seed_database

    # mock payload and event data
    mock_payload_data = {
        'id': 'evt_123456789',
        'type': 'checkout.session.completed',
        'created': 1609459200,
        'data': {
            'object': {
                'id': 'cs_123456789',
                'metadata': {
                    'method': 'STANDARD',
                    'user': str(user.id),
                    'address_id': str(address.id)
                },
                'customer': str(user.id),
                'payment_intent': '123456789'
            },
        }
    }

    # mock the webhook secret
    with patch.dict(config, {'WEBHOOK_SECRET': 'mock_webhook_secret'}) :
        with patch('firebase_admin.auth.verify_id_token', MagicMock(return_value = { 'uid': test_uid })) :
        # mock the stripe event
            with patch('stripe.Webhook.construct_event') as mock_construct_event :
                # return the mock payload data 
                mock_construct_event.return_value = mock_payload_data

                # making request
                response = flask_app.post('/api/order/stripe-webhook',
                    headers = { 'Authorization': f'Bearer {test_uid}' },
                    json = json.dumps(mock_payload_data)
                )

    assert response.status_code == 200
    assert response.json['success'] == True

    # asserting that order was created
    created_order = Order.query.filter_by(user_id = user.id).first()
    assert created_order is not None

    # asserting that order was finalized and address was associated
    assert created_order.shipping_address_id == address.id
    assert created_order.status == Order_Status.PROCESSING
    assert created_order.payment_status == Pay_Status.COMPLETED
    unittest.TestCase().assertDictEqual(created_order.items[0].as_dict(), cart_item.as_dict())

    # asserting that cart item within order was set to ordered = True

    # asserting that user's stripe customer id was updated
    updated_user = User.query.get(user.id)
    assert updated_user.stripe_customer_id == mock_payload_data['data']['object']['customer']

            
@pytest.mark.parametrize('requesting_recents', (True, False))
def test_order_history (flask_app, create_client_user, seed_database, requesting_recents) :
    # create user, get access to address
    user, test_uid = create_client_user
    cart_item, address = seed_database

    # seed in orders, pass in number of iterations / orders to create
    seed_orders(user.id, address.id, 5)

    # query for count of user's orders
    count_of_orders = Order.query.filter_by(user_id = user.id).count()

    # if user is requesting most recent orders, query param of recent=true
    query_params = { 'recent': 'true' } if requesting_recents else {}

    with patch('firebase_admin.auth.verify_id_token', MagicMock(return_value = { 'uid': test_uid })) :
        response = flask_app.get('/api/order/',
            headers = { 'Authorization': f'Bearer {test_uid}' },
            query_string = query_params,
        )

    assert response.status_code in [200, 308]

    # if recent=true query param
    if requesting_recents :
        # asserting that only returned 3 most recent
        assert len(response.json['orders']) is 3

    else :
        # asserting that response sends all the orders
        assert len(response.json['orders']) == count_of_orders


# show order
def test_show_order (flask_app, create_client_user) :
    # create user
    user, test_uid = create_client_user

    # query for order
    order = Order.query.filter_by(user_id = user.id).first()
    assert order is not None

    # format queried order and its items into dictionary
    # convert decimals into strings for assertions against response.json
    order_dict = order.as_dict()
    order_dict['totalPrice'] = str(order.total_price)

    order_dict['items'] = [
        { **item.as_dict(), 'price': str(item.product.price) }
        for item in order.items
    ]


    

    with patch('firebase_admin.auth.verify_id_token', MagicMock(return_value = { 'uid': test_uid })) :
        response = flask_app.get(f'/api/order/{order.id}',
            headers = { 'Authorization': f'Bearer {test_uid}' }
        )

    assert response.status_code in [200, 308]
    unittest.TestCase().assertDictEqual(order_dict, response.json['order'])


# ---- helpers ----

def seed_orders (user_id, address_id, iterations) :
    # formatted to take in number of orders and associated cart items to make
    orders = []
    for _ in range (iterations) :
        # query for product id
        product = Product.query.first()

        order = Order(
            user_id = user_id,
            total_price = product.price,
            date = datetime.datetime.now(),
            status = Order_Status.PENDING,
            stripe_payment_id = None,
            delivery_method = Deliver_Method.STANDARD,
            payment_status = Pay_Status.PENDING,
            shipping_address_id = address_id
        )
        db.session.add(order)
        db.session.commit()

        cart_item = Cart_Item(
            user_id = user_id,
            product_id = product.id,
            portion = Portion.WHOLE,
            quantity = 1,
            ordered = True,
            order_id = order.id
        )
        db.session.add(cart_item)
        db.session.commit()

        orders.append(order)

    return orders