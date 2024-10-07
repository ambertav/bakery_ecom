import pytest
import random
from unittest.mock import patch

from ..database import db
from ..api.models import Cart_Item, Product, Category

@pytest.fixture(scope = 'module')
def seed_products () :

    products = [
        Product(
            name = 'Product 1',
            description = 'Description 1',
            category = Category.COOKIE
        ),
        Product(
            name = 'Product 2',
            description = 'Description 2',
            category = Category.CAKE
        ),
        Product(
            name = 'Product 3',
            description = 'Description 3',
            category = Category.CUPCAKE
        ),
    ]

    try:
        db.session.add_all(products)
        db.session.flush()

        for product in products :
            portions = product.create_portions(10.00)
            db.session.add_all(portions)

        db.session.commit()

        products_details = Product.query.all()

        # returns list of all products for use throughout module tests
        yield products_details

    finally:
        db.session.rollback()
        db.session.close()
 

# creating cart item, scenario: logged in + adding to cart
@pytest.mark.parametrize('valid_product', [True, False])
def test_cart_item_creation (flask_app, user_login, create_client_user, seed_products, valid_product) :
    user_login

    user = create_client_user
    products = seed_products

    if valid_product :
        id = products[0].id
        portion_id = products[0].portions[0].id
    else :
        id = 0
        portion_id = 0

    with patch('flask.request.cookies.get') as mock_get_cookie, \
        patch('backend.api.utils.token.decode_jwt') as mock_decode_jwt :

        mock_get_cookie.return_value = 'valid_access_token'
        mock_decode_jwt.return_value = { 'sub': user.id, 'role': 'user' }

        response = flask_app.post('/api/cart/add', 
            json = { 
                'id': id,
                'portion': portion_id,
                'qty': generate_random_quantity(),
            },
        )

    if valid_product :
        assert response.status_code == 201
        assert response.json['message'] == 'Item added successfully'

    else :
        assert response.status_code == 404
        assert  response.json['error'] == 'Product not found'


# creating cart item, scenario: user has items in cart and then logs in / signs up
def test_auto_cart_item_creation_on_login (flask_app, create_client_user, seed_products) :
    user = create_client_user
    products = seed_products

    previous_cart_item_count = Cart_Item.query.filter_by(user_id = user.id).count()

    cart_item = Cart_Item.query.filter_by(user_id = user.id, product_id = products[0].id).first()
    qty_of_existing_item = cart_item.quantity

    # creating local storage cart with:
        # product id that matches the product id of an existing cart_item
        # product id that does not match 
    localStorageCart = [
        {
            'product': products[0].as_dict(),
            'quantity': 4,
            'portion': products[0].as_dict().get('portions')[0],
        }, 
        {
            'product': products[1].as_dict(),
            'quantity': 2,
            'portion': products[1].as_dict().get('portions')[0],
        },
    ]

    with patch('flask.request.cookies.get') as mock_get_cookie, \
        patch('backend.api.utils.token.decode_jwt') as mock_decode_jwt :

        mock_get_cookie.return_value = 'valid_access_token'
        mock_decode_jwt.return_value = { 'sub': user.id, 'role': 'user' }

        response = flask_app.post('/api/user/login', 
            json = {
                'email': user.email,
                'password': 'password',
                'localStorageCart': localStorageCart
            },
        )

    assert response.status_code == 200
    assert response.json['message'] == 'User logged in successfully'

    cart_items = Cart_Item.query.filter_by(user_id = user.id).all()
    assert len(cart_items) == len(localStorageCart)

    for i, item in enumerate(localStorageCart):
        assert cart_items[i].product_id == item['product'].get('id')

        # for case of existing cart_item product id, quantity should equal sum of existing qty and local storage item qty
            # this is so that duplicates are not created, and instead the quantity is just incremented by the input
            # otherwise, the quantity should be equal
        expected_quantity = item['quantity'] + qty_of_existing_item if i == 0 else item['quantity']

        assert cart_items[i].quantity == expected_quantity


def test_view_cart (flask_app, create_client_user, user_login) :
    user_login

    user = create_client_user
    cart_items = Cart_Item.query.filter_by(user_id = user.id).all()

    with patch('flask.request.cookies.get') as mock_get_cookie, \
        patch('backend.api.utils.token.decode_jwt') as mock_decode_jwt :

        mock_get_cookie.return_value = 'valid_access_token'
        mock_decode_jwt.return_value = { 'sub': user.id, 'role': 'user' }

        response = flask_app.get('/api/cart/')

        assert response.status_code == 200
        assert len(response.json['shopping_cart']) is len(cart_items)

        for i, cart_item in enumerate(cart_items):
            assert response.json['shopping_cart'][i]['product'].get('id') == cart_item.product_id

        
@pytest.mark.parametrize('valid_id, new_qty', [
    (True, 5), # valid id, positive int qty --> should update successfully
    (True, 0), # valid id, zero qty --> delete cart item
    (False, None), # invalid id --> 404
    (True, -1), # valid id, invalid qty --> 500
])
def test_update_cart_item_quantity (flask_app, create_client_user, user_login, valid_id, new_qty) :
    user_login

    user = create_client_user
    cart_items = Cart_Item.query.filter_by(user_id = user.id).all()

    item_id = cart_items[0].id if valid_id else 0

    with patch('flask.request.cookies.get') as mock_get_cookie, \
        patch('backend.api.utils.token.decode_jwt') as mock_decode_jwt :

        mock_get_cookie.return_value = 'valid_access_token'
        mock_decode_jwt.return_value = { 'sub': user.id, 'role': 'user' }

        response = flask_app.put(f'/api/cart/{item_id}/update', 
            json = { 'newQty': new_qty },
        )

        if valid_id and new_qty >= 0 :
            assert response.status_code == 200
            assert response.json['message'] == 'Item quantity updated successfully'

            updated_cart_item = Cart_Item.query.filter_by(user_id = user.id, id = item_id).first()

            if new_qty > 0 :
                assert updated_cart_item.quantity == new_qty
            elif new_qty == 0 :
                # should return None because the item was deleted
                assert updated_cart_item is None

        # if quantity is negative, error
        elif valid_id and new_qty < 0 :
            assert response.status_code == 400

        # else not valid id, error
        else :
            assert response.status_code == 404
            assert response.json['error'] == 'Item not found in cart'


@pytest.mark.parametrize('valid_id', [
    (True), # valid id, cart item exists --> will be deleted
    (False) # invalid id, cart item does not exist --> 404
])
def test_delete_cart_item (flask_app, create_client_user, user_login, valid_id) :
    user_login

    user = create_client_user
    cart_items = Cart_Item.query.filter_by(user_id = user.id).all()

    previous_length = len(cart_items)

    item_id = cart_items[0].id if valid_id else 0

    with patch('flask.request.cookies.get') as mock_get_cookie, \
        patch('backend.api.utils.token.decode_jwt') as mock_decode_jwt :

        mock_get_cookie.return_value = 'valid_access_token'
        mock_decode_jwt.return_value = { 'sub': user.id, 'role': 'user' }

        response = flask_app.delete(f'/api/cart/{item_id}/delete')

    if valid_id :
        assert response.status_code == 200
        assert response.json['message'] == 'Item deleted from cart successfully'

        # asserting that the count of user's cart items was decremented
        updated_cart_items_count = Cart_Item.query.filter_by(user_id = user.id).count()
        assert updated_cart_items_count == previous_length - 1

        # query for deleted cart item should return None
        deleted_cart_item = Cart_Item.query.filter_by(user_id = user.id, id = item_id).first()
        assert deleted_cart_item is None
    else :
        assert response.status_code == 404
        assert response.json['error'] == 'Item not found in cart'



# ---- helpers ----

# for use to determine a random quantity for cart item, given as range of 1 to 10 for simplicity
def generate_random_quantity () :
    return random.randint(1, 10)


def create_and_add_cart_item(product_id, user_id, portion_id) :
    cart_item = Cart_Item(
        product_id = product_id,
        user_id = user_id,
        portion_id = portion_id,
        quantity = 2,
        ordered = False,
        order_id = None,
    )

    db.session.add(cart_item)
    db.session.commit()

    return cart_item