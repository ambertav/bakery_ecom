from flask import Blueprint, jsonify, request, current_app

from ...database import db
from ..utils.auth import auth_user
from ..models.models import Product, Category, Role

product_bp = Blueprint('product', __name__)


@product_bp.route('/', methods = ['GET'])
def product_index () :
    try :
        # extract page and params
        page = request.args.get('page', 1, type = int)
        category = request.args.get('category')
        search = request.args.get('search')

        # base query to build upon based on params 
        base_query = Product.query

        if category :
            base_query = base_query.filter_by(category = Category[category])

        if search :
            base_query = base_query.filter(Product.name.ilike(f'%{search}%'))

        # query with pagination
        products = base_query.paginate(page = page, per_page = 10)

        # if products are returned,
        if products.items :
            # format products using as_dict()
            products_list = [ product.as_dict() for product in products.items if product.stock > 0 ]
            
            return jsonify({
                'products': products_list,
                'totalPages': products.pages,
                'currentPage': page
            }), 200
        
        # otherwise, return empty array
        else :
            return jsonify({
                'products': [],
                'message': 'No products found'
            }), 200
        
    except Exception as error :
        current_app.logger.error(f'Error fetching products: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500

@product_bp.route('/create', methods = ['POST'])
def create_product () :
    try :
        # retrieve token and auth user
        user = auth_user(request)

        if user is None :
            return jsonify({
                'error': 'Authentication failed'
            }), 401
        elif user.role != Role.ADMIN :
            return jsonify({
                'error': 'Forbidden'
            }), 403
        
        data = request.get_json()

        product_data = {
            key: data.get(key) for key in ['name', 'description', 'category', 'image', 'price', 'stock']
        }

        new_product = Product(**product_data)

        db.session.add(new_product)
        db.session.commit()

        return jsonify({
            'message': 'Product created successfully'
        }), 201
    
    except Exception as error :
        current_app.logger.error(f'Error creating product: {str(error)}')
        return jsonify({
            'error': error
        }), 500
    

@product_bp.route('/<int:id>/update', methods = ['PUT'])
def product_update (id) :
    try :
        # retrieve token and auth user
        user = auth_user(request)

        if user is None :
            return jsonify({
                'error': 'Authentication failed'
            }), 401
        elif user.role != Role.ADMIN :
            return jsonify({
                'error': 'Forbidden'
            }), 403
        

        product = Product.query.get(id)

        if product :
            data = request.get_json()
            for key, value in data.items() :
                if hasattr(product, key) and getattr(product, key) != value :
                    setattr(product, key, value)
            db.session.commit()

            return jsonify({
                'message': 'Product updated successfully'
            }), 200
        
        else :
            return jsonify({
                'error': 'Product not found'
            }), 404

    except Exception as error :
        current_app.logger.error(f'Error updating product: {str(error)}')
        return jsonify({
            'error': error
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
