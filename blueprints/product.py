from flask import Blueprint, jsonify, current_app

from ..app import db
from ..models import Product

product_bp = Blueprint('product', __name__)


@product_bp.route('/')
def index () :
    return 'Hello from products!'

@product_bp.route('/test')
def test () :
    return 'testing from products!'


@product_bp.route('/create')
def create_product () :
    try :
        new_product = Product(
            name = 'another test',
            description = 'testing...',
            image = 'test.url',
            price = 999.99,
            stock = 1,
        )

        db.session.add(new_product)
        db.session.commit()

        return jsonify({
            'message' : 'Product created successfully'
        })
    except Exception as error :
        current_app.logger.error(f'Error creating product: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500