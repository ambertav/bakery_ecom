from flask import Blueprint, jsonify, request, current_app
from sqlalchemy import text, func
from sqlalchemy.orm import joinedload


from ...database import db
from ..utils.auth import auth_admin
from ..models.product import Product, Category
from ..models.portion import Portion

from ..utils.aws_s3 import s3_photo_upload

product_bp = Blueprint('product', __name__)


@product_bp.route('/', methods = ['GET'])
def product_index () :
    try :
        # extract page and params
        page = request.args.get('page', 1, type = int)
        category = request.args.get('category')
        search = request.args.get('search')
        sort = request.args.get('sort')

        # base query to build upon based on params 
        base_query = Product.query

        if category :
            # adding cateogry filter to query, use uppercase for enum
            base_query = base_query.filter_by(category = Category[category.upper()])

        if sort and sort != 'recommended':
            # to map sort options, utilizing text() in query
            sort_options = {
                'priceAsc': 'price ASC',
                'priceDesc': 'price DESC',
                'nameAsc': 'name ASC',
                'nameDesc': 'name DESC',
            }
            
            sort_option = sort_options.get(sort)

            if sort_option :
                # adding sort to query
                base_query = base_query.order_by(text(sort_option))

        if search :
            base_query = base_query.filter(Product.name.ilike(f'%{search}%'))

        # sub query to push products with no portions in stock down to the bottom
        sub_query = db.session.query(
            func.sum(Portion.stock).label('total_stock')
            ).filter(Portion.product_id == Product.id
            ).group_by(Portion.product_id).scalar_subquery()
        
        base_query = base_query.order_by(func.coalesce(sub_query, 0).desc())

        # applying query with pagination
        products = base_query.paginate(page = page, per_page = 10)

        # if products are returned...
        if products.items :
            
            products_list = [ product.as_dict() for product in products.items ]
            
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
        admin = auth_admin(request)

        if admin is None :
            return jsonify({
                'error': 'Authentication failed'
            }), 401
        
        data = request.get_json()

        product_data = {
            key: data.get(key) for key in ['name', 'description', 'category', 'image']
        }

        try :
            new_product = Product(**product_data)
            db.session.add(new_product)
            db.session.flush()

            portions = new_product.create_portions(data.get('price'))

            for portion in portions :
                db.session.add(portion)

            db.session.commit()
            db.session.refresh(new_product)


        except Exception as error :
            db.session.rollback()
            raise error

        return jsonify({
            'product': new_product.as_dict(),
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
        admin = auth_admin(request)

        if admin is None :
            return jsonify({
                'error': 'Authentication failed'
            }), 401
        
        product = Product.query.get(id)

        if product :
            product.update_attributes(request.get_json())
            db.session.commit()

            return jsonify({
                'product': product.as_dict(),
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
    

@product_bp.route('<int:id>/upload_photo', methods = ['POST'])
def product_upload_photo (id) :
    try :
        if 'image' not in request.files:
            return jsonify({
                'error': 'No image file found in request'
            }), 400
        
        product = Product.query.get(id)

        if not product :
            return jsonify({
                'error': 'Product not found'
            }), 404

        file = request.files.get('image')
        image_url = s3_photo_upload(file, str(product.id))

        if image_url :
            product.update_attributes({'image': image_url})
            db.session.commit()

            return jsonify({
                'message': 'Image uploaded successfully',
            }), 200

    except Exception as error :
        current_app.logger.error(f'Error uploading product image: {str(error)}')
        return jsonify({
            'error': error
        }), 500


@product_bp.route('/inventory/generate-report', methods = ['GET'])
def product_generate_inventory_report () :
    try :
        # retrieve token and auth user
        admin = auth_admin(request)

        if admin is None :
            return jsonify({
                'error': 'Authentication failed'
            }), 401
        
        low_stock_products = (Product.query
            .join(Product.portions)
            .filter(Portion.stock < (Portion.optimal_stock - 5)) # filtering where stock is below ideal threshold
            .distinct()  # ensures product only comes up once
            .options(joinedload(Product.portions))
            .all()
        )
        
        products_list = []
        portions_to_update = {}

        for product in low_stock_products :
            # filter for portions based on stock criteria 
            filtered_portions = [
                portion for portion in product.portions
                if portion.stock < (portion.optimal_stock - 5)
            ]
            
            if filtered_portions :
                # update product with list of filtered portions and convert to dict
                product.portions = filtered_portions
                products_list.append(product.as_dict())

                # construct the updatedPortionsState structure with the portions that need stock updates for frontend
                if product.id not in portions_to_update :
                    portions_to_update[product.id] = {}

                for portion in filtered_portions :
                    portions_to_update[product.id][portion.id] = portion.optimal_stock - portion.stock


        return jsonify({
            'products': products_list,
            'updatedPortionsState': portions_to_update
        }), 200
        

    except Exception as error :
        current_app.logger.error(f'Error generating inventory report: {str(error)}')
        return jsonify({
            'error': error
        }), 500



@product_bp.route('/inventory/update', methods = ['PUT'])
def product_update_inventory () :
    try :
        admin = auth_admin(request)

        # restrict access to only admin users
        if admin is None :
            return jsonify({
                'error': 'Authentication failed'
            }), 401

        data = request.get_json()

        try :
            # loop over data, and extract the product id key, portion id and new stock value
            for product_id, portions in data.items() :
                # retrieve product
                product = Product.query.get(int(product_id))
                if product :
                    for portion_id, new_stock in portions.items() :
                        # retrieve portion and update stock
                        portion = next((p for p in product.portions if p.id == int(portion_id)), None)
                        if portion :
                            portion.update_stock(int(new_stock))
                        
                        else :
                            raise ValueError(f'Portion with id {portion_id} was not found')
                        
                else :
                    raise ValueError(f'Product with id {product_id} was not found')
            
            # commit the transaction
            db.session.commit()

        except Exception as error :
            db.session.rollback()  # rollback transaction if error
            raise 


        return jsonify({
            'message': 'Inventory updated successfully'
        }), 200
    
    except Exception as error :
        current_app.logger.error(f'Error updating inventory: {str(error)}')
        return jsonify({
            'error': f'Error updating inventory: {str(error)}'
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
