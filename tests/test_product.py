import pytest
import unittest
import random

from sqlalchemy.exc import IntegrityError

from ..database import db
from ..api.models.models import Product, Category


# model validation tests
@pytest.mark.parametrize('name, description, category, image, price, stock, valid', [
    ('Product 1', 'Description 1', Category.CAKE, 'https://example.com/image.jpg', 10.00, 100, True),  # valid
    ('Product 2', 'Description 2', Category.CUPCAKE, 'https://example.com/image.jpg', -5.00, 100, False),  # invalid, violates negative price
    ('Product 3', 'Description 3', Category.PIE, 'https://example.com/image.jpg', 10.00, -50, False),  # invalid, violates negative stock
    ('Product 4', 'Description 4', Category.CAKE, 'image.png', 10.00, 100, False),  # invalid, violates image string format
])
def test_product_validation(flask_app, name, description, category, image, price, stock, valid) :
    if valid :
        # base case with valid data, should create product
        create_and_add_product(name, description, category, image, price, stock)
        added_product = Product.query.filter_by(name = name).first()
        assert added_product is not None
    else:
        # testing column constraints by asserting presence of IntegrityError
        with pytest.raises(IntegrityError) as error :
            create_and_add_product(name, description, category, image, price, stock)
        db.session.rollback() # rollback failed transaction in database 
        assert error.type is IntegrityError # assert IntegrityError


# controller logic tests
@pytest.mark.parametrize('role', ['ADMIN', 'CLIENT'])
def test_product_creation(flask_app, create_admin_user, create_client_user, mock_firebase, role) :
    # creates users with different roles
    if role == 'ADMIN' :
        admin, test_uid = create_admin_user 
    else :
        user, test_uid = create_client_user

    # req to create product
    with mock_firebase(test_uid) :
        response = flask_app.post('/api/product/create', 
            headers = { 'Authorization': f'Bearer {test_uid}' }, 
            json = {
                'name': 'Admin Test Product',
                'description': 'Test Description',
                'category': 'COOKIE',
                'image': 'https://example.com/image.jpg',
                'price': 10.0,
                'stock': 0
            },
        )

    if role == 'ADMIN' :
        # admin user should create product
        assert response.status_code == 201
        assert response.json['message'] == 'Product created successfully'
    else:
        # client user should get auth failed
        assert response.status_code == 401
        assert response.json['error'] == 'Authentication failed'
    
    # runs for both tests to assert only admin's product was created
    count_of_products = Product.query.filter_by(name = 'Admin Test Product').count()
    assert count_of_products is 1

@pytest.mark.parametrize('requesting_category, searching', [
    (False, False), # no category or search params
    (True, False), # category param
    (False, True), # search param
    (True, True) # category and search param
])
def test_product_index (flask_app, requesting_category, searching) :
    # initalize param strings
    category_param = random.choice(list(Category)).value if requesting_category else ''
    search_param = 'product 1' if searching else ''

    # construct params
    query_params = { key: value for key, value in [('category', category_param), ('search', search_param)] if value }

    response = flask_app.get('/api/product/', 
        query_string = query_params
    )

    assert response.status_code in [200, 308]

    # base query for count of products
    count_query = Product.query

    # if category param, count products within that category
    if requesting_category :
        count_query = count_query.filter_by(category = category_param)
    
    # if search param, count products that match search
    if searching :
        count_query = count_query.filter(Product.name.ilike(f'%{search_param}%'))

    # assert that length of response products equals count of products
    count_of_products = count_query.filter(Product.stock > 0).count()
    assert len(response.json['products']) == count_of_products

    # asserting message if no products
    if count_of_products is 0 :
        unittest.TestCase().assertListEqual([], response.json['products'])
        assert response.json['message'] == 'No products found'


@pytest.mark.parametrize('role', ['ADMIN', 'CLIENT'])
def test_view_of_product_index (flask_app, create_admin_user, create_client_user, mock_firebase, role) :
    if role == 'ADMIN' :
        admin, test_uid = create_admin_user
    else :
        user, test_uid = create_client_user

    with mock_firebase(test_uid) :
        response = flask_app.get('/api/product/', 
            headers = { 'Authorization': f'Bearer {test_uid}' }, 
        )
    
    assert response.status_code in [200, 308]

    if role == 'ADMIN' :
        # asserting that admin get out of stock products returned (all products)
        count_of_products = Product.query.count()
        assert len(response.json['products']) is count_of_products
    
    else :
        # aasserting that clients only get in stock products
        count_of_products = Product.query.filter(Product.stock > 0).count()
        assert len(response.json['products']) is count_of_products


def test_product_show (flask_app) :
    product = Product.query.filter_by(name = 'Product 1').first()
    assert product is not None

    # convert price and stock to a string for last assertions against response product
    product.price = str(product.price)
    product.stock = str(product.stock)

    response = flask_app.get(f'/api/product/{product.id}')

    assert response.status_code in [200, 308]
    unittest.TestCase().assertDictEqual(product.as_dict(), response.json['product'])


@pytest.mark.parametrize('role, valid_product', [
    ('ADMIN', True),
    ('ADMIN', False),
    ('CLIENT', None),
])
def test_product_update (flask_app, create_admin_user, create_client_user, mock_firebase, role, valid_product) :
    # creates users with different roles
    if role == 'ADMIN' :
        admin, test_uid = create_admin_user 
    else :
        user, test_uid = create_client_user

    if valid_product :
        product = Product.query.first()
        product_id = product.id
    else :
        product_id = 0
    
    updated_data = {
        'name': 'Updated product',
        'description': 'updated description',
        'stock': 10,
    }

    # req to edit product
    with mock_firebase(test_uid) :
        response = flask_app.put(f'/api/product/{product_id}/update', 
            headers = { 'Authorization': f'Bearer {test_uid}' }, 
            json = updated_data
        )
    
    if role == 'ADMIN' and valid_product :
        assert response.status_code == 200
        assert response.json['message'] == 'Product updated successfully'

        updated_product = Product.query.get(product_id)

        for field, value in updated_data.items():
            assert getattr(updated_product, field) == value

    elif role == 'ADMIN' and not valid_product :
        assert response.status_code == 404
        assert response.json['error'] == 'Product not found'

    else :
        assert response.status_code == 401
        assert response.json['error'] == 'Authentication failed'


@pytest.mark.parametrize('valid_product_ids', [True, False])
def test_product_update_inventory (flask_app, create_admin_user, mock_firebase, valid_product_ids) :
    user, test_uid = create_admin_user

    if valid_product_ids :
        # query for valid product ids
        product_ids = db.session.query(Product.id).limit(2)

        # dict comprehension to form structure of {'product.id': 'new stock value'}
        # query returns ids as tuple, and will have to convert to strings
        new_stock_value = str(random.randint(0, 50))
        input = { str(id[0]): new_stock_value for id in product_ids }

    else :
        input = {
            '0': '50',
            '0': '60',
        }

    # req to edit product
    with mock_firebase(test_uid) :
        response = flask_app.put('/api/product/inventory/update', 
            headers = { 'Authorization': f'Bearer {test_uid}' }, 
            json = input
        )

    if valid_product_ids :
        assert response.status_code == 200
        assert response.json['message'] == 'Inventory updated successfully'

        # retrieve one of the product ids to assert new stock value
        updated_product = Product.query.get(product_ids[0][0])
        assert updated_product.stock == int(new_stock_value)

    else :
        assert response.status_code == 500
    

# ---- helpers ----

def create_and_add_product(name, description, category, image, price, stock) :
    product = Product(
        name = name,
        description = description,
        category = category,
        image = image,
        price = price,
        stock = stock
    )
    db.session.add(product)
    db.session.commit()

    return product
