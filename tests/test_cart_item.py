import pytest
import random

from unittest.mock import patch, MagicMock

from ..database import db
from ..api.models.models import Cart_Item, Portion, Product, Category


@pytest.fixture(scope = 'module')
def seed_products (flask_app) :
    products_data = [
        {
            'name': 'Product 1',
            'description': 'Description 1',
            'category': Category.COOKIE,
            'image': 'https://example.com/image.png',
            'price': 10.00,
            'stock': 100
        },
        {
            'name': 'Product 2',
            'description': 'Description 2',
            'category': Category.CAKE,
            'image': 'https://example.com/image.jpg',
            'price': 15.00,
            'stock': 150
        },
        {
            'name': 'Product 3',
            'description': 'Description 3',
            'category': Category.CUPCAKE,
            'image': 'https://example.com/image.gif',
            'price': 20.00,
            'stock': 200
        }
    ]

    session = db.session()

    try:
        # insert products in bulk
        session.bulk_insert_mappings(Product, products_data)
        session.commit()

        # returns list of all products for use throughout module tests
        yield Product.query.all()

    finally:
        session.rollback()
        session.close()
 

# creating cart item, scenario: logged in + adding to cart
@pytest.mark.parametrize('valid_product', [True, False])
def test_cart_item_creation (flask_app, create_client_user, seed_products, valid_product) :
    # create user and get list of products
    user, test_uid = create_client_user
    products = seed_products

    # if valid test,
    if valid_product : 
        id = products[0].id
    else :
        # otherwise, initialize id with an invalid id
        id = 0

    with patch('firebase_admin.auth.verify_id_token', MagicMock(return_value = { 'uid': test_uid })) :
        response = flask_app.post('/api/cart/add', 
            headers = { 'Authorization': f'Bearer {test_uid}' },
            json = { 
                'id': id,
                'qty': generate_random_quantity(),
                'portion': 'WHOLE'
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
    # create user and get list of products
    user, test_uid = create_client_user
    products = seed_products

    previous_cart_item_count = Cart_Item.query.filter_by(user_id = user.id).count()

    # query for existing cart items starting quantity
    cart_item = Cart_Item.query.filter_by(user_id = user.id, product_id = products[0].id).first()
    qty_of_existing_item = cart_item.quantity

    # creating local storage cart with:
        # product id that matches the product id of an existing cart_item
        # product id that does not match 
    localStorageCart = [
        {
            'productId': products[0].id,
            'quantity': 4,
            'portion': 'WHOLE',
        }, 
        {
            'productId': products[1].id,
            'quantity': 2,
            'portion': 'WHOLE',
        },
    ]

    with patch('firebase_admin.auth.verify_id_token', MagicMock(return_value = { 'uid': test_uid })) :
        response = flask_app.post('/api/user/login', 
            headers = { 'Authorization': f'Bearer {test_uid}' },
            json = {
                'name': 'test',
                'localStorageCart': localStorageCart
            },
        )

    assert response.status_code == 200
    assert response.json['message'] == 'User logged in successfully'

    # query all cart_items for the user, assert length
    cart_items = Cart_Item.query.filter_by(user_id = user.id).all()
    assert len(cart_items) == len(localStorageCart)

    # loop to go through and assert product id and quantities of cart_items
    for i, item in enumerate(localStorageCart):
        assert cart_items[i].product_id == item['productId']

        # for case of existing cart_item product id, quantity should equal sum of existing qty and local storage item qty
            # this is so that duplicates are not created, and instead the quantity is just incremented by the input
            # otherwise, the quantity should be equal
        expected_quantity = item['quantity'] + qty_of_existing_item if i == 0 else item['quantity']

        assert cart_items[i].quantity == expected_quantity


@pytest.mark.parametrize('category, is_valid_portion', [
    (Category.COOKIE, True),
    (Category.COOKIE, False),
    (Category.CAKE, True),
    (Category.CAKE, False),
    (Category.CUPCAKE, True),
    (Category.CUPCAKE, False),
])
def test_cart_item_portion_and_price_validation (flask_app, create_client_user, seed_products, category, is_valid_portion) :
    user, test_uid = create_client_user
    seed_products

    # create dictionary of valid portions for each of the tested categories
    valid_portion_options = {
        Category.COOKIE: [Portion.WHOLE],
        Category.CUPCAKE: [Portion.WHOLE, Portion.MINI],
        Category.CAKE: [Portion.WHOLE, Portion.MINI, Portion.SLICE],
    }

    # query for product for use in cart item creation
    product = Product.query.filter_by(category = category).first()

    if is_valid_portion :
        # get valid portion option
        portion = valid_portion_options[category][0]

        # with valid data, should create cart_item
        cart_item = create_and_add_cart_item(product.id, user.id, portion)
        created_item = Cart_Item.query.get(cart_item.id)
        assert created_item is not None

        # map out price multipler based on portion
        portion_multiplier_mapping = {
            Portion.WHOLE: 1,
            Portion.MINI: 0.5,
            Portion.SLICE: 0.15
        }

        # get the expected price multiplier
        expected_multiplier = portion_multiplier_mapping.get(portion)

        # define a tolerance for comparison
        tolerance = 0.01

        # assert that the price reflects expected price multiplier within the given tolerance
        assert abs(created_item.price / product.price - expected_multiplier) <= tolerance

    else :
        with pytest.raises(ValueError) as error :
            # get invalid portion option 
            invalid_options = [portion for portion in Portion if portion not in valid_portion_options[category]]

            if invalid_options :
                portion = invalid_options[0] 
            else :
                # if no invalid options (such as for cakes and pies that come in all options), set portion to 'INVALID'
                # this should violate enum, and returns ValueError 
                portion = 'INVALD'

            # testing portion column constraints, should return ValueError
            cart_item = create_and_add_cart_item(product.id, user.id, portion)
        
        db.session.rollback # rollback failed transaction in database
        assert error.type is ValueError # assert ValueError


def test_view_cart (flask_app, create_client_user) :
    # creating user, query for all of user's cart items
    user, test_uid = create_client_user
    cart_items = Cart_Item.query.filter_by(user_id = user.id).all()

    with patch('firebase_admin.auth.verify_id_token', MagicMock(return_value = { 'uid': test_uid })) :
        response = flask_app.get('/api/cart/', 
            headers = { 'Authorization': f'Bearer {test_uid}' },
        )

    assert response.status_code in [200, 308]
    # assert response returns all cart items
    assert len(response.json['shopping_cart']) is len(cart_items)

    # assert that product id for each matches
    for i, cart_item in enumerate(cart_items):
        assert response.json['shopping_cart'][i]['productId'] == cart_item.product_id

        
@pytest.mark.parametrize('valid_id, new_qty', [
    (True, 5), # valid id, positive int qty --> should update successfully
    (True, 0), # valid id, zero qty --> delete cart item
    (False, None), # invalid id --> 404
    (True, -1), # valid id, invalid qty --> 500
])
def test_update_cart_item_quantity (flask_app, create_client_user, valid_id, new_qty) :
    # creating user, query for all of user's cart items
    user, test_uid = create_client_user
    cart_items = Cart_Item.query.filter_by(user_id = user.id).all()

    if valid_id :
        item_id = cart_items[0].id
    else :
        item_id = 0

    with patch('firebase_admin.auth.verify_id_token', MagicMock(return_value = { 'uid': test_uid })) :
        response = flask_app.put(f'/api/cart/{item_id}/update', 
            headers = { 'Authorization': f'Bearer {test_uid}' },
            json = {
                'newQty': new_qty
            },
        )

    if valid_id and new_qty >= 0 :
        assert response.status_code == 200
        assert response.json['message'] == 'Item quantity updated successfully'

        # query for update
        updated_cart_item = Cart_Item.query.filter_by(user_id = user.id, id = item_id).first()

        # if the quantity to update to is greater than 0
        if new_qty > 0 :
            # assert that the quantities match
            assert updated_cart_item.quantity == new_qty
        elif new_qty == 0 :
            # else the query should return None because the item was deleted
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
def test_delete_cart_item (flask_app, create_client_user, valid_id) :
    # creating user, query for all of user's cart items
    user, test_uid = create_client_user
    cart_items = Cart_Item.query.filter_by(user_id = user.id).all()

    # storing previous length to verify if one was deleted
    previous_length = len(cart_items)

    if valid_id : 
        item_id = cart_items[0].id
    else :
        item_id = 0

    with patch('firebase_admin.auth.verify_id_token', MagicMock(return_value = { 'uid': test_uid })) :
        response = flask_app.delete(f'/api/cart/{item_id}/delete', 
            headers = { 'Authorization': f'Bearer {test_uid}' },
        )

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


def create_and_add_cart_item(product_id, user_id, portion) :
    cart_item = Cart_Item(
        product_id = product_id,
        user_id = user_id,
        portion = portion,
        quantity = 2,
        ordered = False,
        order_id = None,
    )
    db.session.add(cart_item)
    db.session.commit()

    return cart_item