import pytest
import unittest
import random
import os


from unittest.mock import patch
from sqlalchemy.exc import IntegrityError

from ..database import db
from ..api.models import Product, Category, Role


@pytest.mark.parametrize('valid_image', [True, False])
def test_product_validation(valid_image) :
    product = Product(
        name = 'Product 1',
        description = 'Description 1',
        category = Category.CAKE
    )

    db.session.add(product)
    db.session.commit()
    db.session.refresh(product)

    image_url = "https://s3.amazonaws.com/bucket/images/product123.jpg" if valid_image else "invalid"

    if valid_image :
        product.update_attributes({ 'image': image_url })
        assert product.image == image_url
    else :
        with pytest.raises(IntegrityError) as error :
            product.update_attributes({ 'image': image_url })
            db.session.commit()

        db.session.rollback() # rollback failed transaction in database 
        assert error.type is IntegrityError



# controller logic tests
@pytest.mark.parametrize('role', [Role.SUPER, Role.MANAGER, Role.GENERAL])
def test_product_creation(flask_app, create_admin_user, admin_login, role) :
    admin_login
    admin = create_admin_user

    admin.role = role
    db.session.commit()

    image_path = os.path.join(os.path.dirname(__file__), 'pytestlogo.png')

    with patch('flask.request.cookies.get') as mock_get_cookie, \
        patch('backend.api.utils.token.decode_jwt') as mock_decode_jwt :

        mock_get_cookie.return_value = 'valid_access_token'
        mock_decode_jwt.return_value = { 'sub': admin.id, 'role': 'admin' }

        with open(image_path, 'rb') as image_file:
            response = flask_app.post('/api/product/create', 
                content_type = 'multipart/form-data',
                data = {
                    'name': 'Test Product',
                    'description': 'Test Description',
                    'category': 'COOKIE',
                    'price': 10.00,
                    'image': (image_file, 'pytestlogo.png')
                },
        )

    if role == Role.SUPER :
        assert response.status_code == 201
        assert response.json['message'] == 'Product created successfully'
        
    else :
        # client user should get auth failed
        assert response.status_code == 403
        assert response.json['error'] == 'Forbidden'
    
    # runs for all tests to assert only SUPER admin's product was created
    count_of_created_products = Product.query.filter_by(name = 'Test Product').count()
    assert count_of_created_products is 1


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
    count_of_products = count_query.count()
    assert len(response.json['products']) == count_of_products

    # asserting message if no products
    if count_of_products == 0 :
        unittest.TestCase().assertListEqual([], response.json['products'])
        assert response.json['message'] == 'No products found'

def test_product_show (flask_app) :
    product = Product.query.filter_by(name = 'Product 1').first()
    assert product is not None

    response = flask_app.get(f'/api/product/{product.id}')

    assert response.status_code in [200, 308]
    unittest.TestCase().assertDictEqual(product.as_dict(), response.json['product'])


@pytest.mark.parametrize('role, valid_product', [
    (Role.SUPER, True),
    (Role.SUPER, False),
    ( Role.MANAGER, True),
    ( Role.MANAGER, False),
    (Role.GENERAL, None),
])
def test_product_update (flask_app, create_admin_user, admin_login, role, valid_product) :
    admin_login
    admin = create_admin_user

    admin.role = role
    db.session.commit()

    product = Product.query.first()
    product_id = product.id if valid_product else 0

    updated_data = {
        'name': 'updated product',
        'description': 'updated description',
    }

    with patch('flask.request.cookies.get') as mock_get_cookie, \
        patch('backend.api.utils.token.decode_jwt') as mock_decode_jwt :

        mock_get_cookie.return_value = 'valid_access_token'
        mock_decode_jwt.return_value = { 'sub': admin.id, 'role': 'admin' }

        response = flask_app.put(f'/api/product/{product_id}/update', data = updated_data)
    
    if role != Role.GENERAL and valid_product :
        assert response.status_code == 200
        assert response.json['message'] == 'Product updated successfully'

        updated_product = Product.query.get(product_id)

        for field, value in updated_data.items():
            assert getattr(updated_product, field) == value

    elif role != Role.GENERAL and not valid_product :
        assert response.status_code == 404
        assert response.json['error'] == 'Product not found'

    else :
        assert response.status_code == 403
        assert response.json['error'] == 'Forbidden'

@pytest.mark.parametrize('valid_products, valid_portions', [
    (True, True),
    (True, False),
    (False, None)
])
def test_product_update_inventory (flask_app, create_admin_user, admin_login, valid_products, valid_portions) :
    admin_login
    admin = create_admin_user

    input = {}
    previous_stock = []

    if valid_products :
        products = Product.query.filter(Product.portions.any()).limit(2).all()

        for product in products :
            if valid_portions : 
                previous_stock.append(product.portions[0].stock)
                
                new_stock_value = str(random.randint(0, 50))
                input[str(product.id)] = { str(product.portions[0].id): new_stock_value }
            else :
                input[str(product.id)] = { '0': '25' }

    else :
        input = {
            '0': { '0': 10 },
            '0': { '0': 20 },
        }

    with patch('flask.request.cookies.get') as mock_get_cookie, \
        patch('backend.api.utils.token.decode_jwt') as mock_decode_jwt :

        mock_get_cookie.return_value = 'valid_access_token'
        mock_decode_jwt.return_value = { 'sub': admin.id, 'role': 'admin' }
        
        response = flask_app.put('/api/product/inventory/update', json = input)

    if valid_products and valid_portions :
        assert response.status_code == 200
        assert response.json['message'] == 'Inventory updated successfully'

        # retrieve one of the product ids to assert new stock value
        updated_product = Product.query.get(products[0].id)
        assert updated_product.portions[0].stock == previous_stock[0] + int(new_stock_value)

    else :
        assert response.status_code == 500