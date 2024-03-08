import pytest
import unittest

from unittest.mock import patch, MagicMock
from sqlalchemy.exc import IntegrityError

from ..database import db
from ..api.models.models import Product, Category


# model validation tests
@pytest.mark.parametrize('name, description, category, image, price, stock, valid', [
    ('Product 1', 'Description 1', Category.CAKE, 'https://example.com/image.jpg', 10.00, 100, True),  # valid
    ('Product 2', 'Description 2', Category.CAKE, 'https://example.com/image.jpg', -5.00, 100, False),  # invalid, violates negative price
    ('Product 3', 'Description 3', Category.CAKE, 'https://example.com/image.jpg', 10.00, -100, False),  # invalid, violates negative stock
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
def test_product_creation(flask_app, create_admin_user, create_client_user, role) :
    # creates users with different roles
    if role == 'ADMIN' :
        user, test_uid = create_admin_user 
    else :
        user, test_uid = create_client_user

    # req to create product
    with patch('firebase_admin.auth.verify_id_token', MagicMock(return_value = { 'uid': test_uid })) :
        response = flask_app.post('/api/product/create', 
            headers = { 'Authorization': f'Bearer {test_uid}' }, 
            json = {
                'name': 'Admin Test Product',
                'description': 'Test Description',
                'category': 'COOKIE',
                'image': 'https://example.com/image.jpg',
                'price': 10.0,
                'stock': 100
            },
        )

    if role == 'ADMIN' :
        # admin user should create product
        assert response.status_code == 201
        assert response.json['message'] == 'Product created successfully'
    else:
        # client user should get access forbidden
        assert response.status_code == 403
        assert response.json['error'] == 'Forbidden'
    
    # runs for both tests to assert only admin's creation should go through
    count_of_products = Product.query.filter_by(name = 'Admin Test Product').count()
    assert count_of_products is 1


def test_product_index (flask_app) :
    count_of_products = Product.query.count()

    response = flask_app.get('/api/product/')

    assert response.status_code in [200, 308]
    assert len(response.json['products']) == count_of_products

def test_product_show (flask_app) :
    product = Product.query.filter_by(name = 'Product 1').first()
    assert product is not None

    # convert price to a string for last assertions against response product
    product.price = str(product.price)

    response = flask_app.get(f'/api/product/{product.id}')

    assert response.status_code in [200, 308]
    unittest.TestCase().assertDictEqual(product.as_dict(), response.json['product'])


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
