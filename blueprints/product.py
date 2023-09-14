from flask import Blueprint, jsonify, request, current_app

from ..app import db
from ..models import Product

product_bp = Blueprint('product', __name__)


@product_bp.route('/')
def index () :
    return 'Hello from products!'

@product_bp.route('/create', methods = ['POST'])
def create_product () :
    try :
        data = request.get_json()

        product_data = {
            key: data.get(key) for key in ['name', 'description', 'image', 'price', 'stock']
        }

        new_product = Product(**product_data)

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