from flask import Blueprint, jsonify, request, current_app

from ...app import db
from ..models.models import Product

product_bp = Blueprint('product', __name__)


@product_bp.route('/', methods = ['GET'])
def product_index () :
    try :
        products = Product.query.all()

        if products :
            # list of products in stock
            products_list = [
                product.as_dict() for product in products if product.stock > 0 # .as_dict() formats product
            ]
        
            return jsonify({
                'products': products_list
            }), 200
        else :
            return jsonify({
                'error': 'Products not found'
            }), 404
        
    except Exception as error :
        current_app.logger.error(f'Error fetching products: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500

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
        }), 201
    except Exception as error :
        current_app.logger.error(f'Error creating product: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500
    
@product_bp.route('/<int:id>', methods = ['GET'])
def product_show (id) :
    try :
        product = Product.query.get(id)

        if product :
            product_detail = product.as_dict()

            return jsonify({
                'product': product_detail
            }), 200
        else :
            return jsonify({
                'error': 'Product not found'
            }), 404
    except Exception as error :
        current_app.logger.error(f'Error fetching product: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500
