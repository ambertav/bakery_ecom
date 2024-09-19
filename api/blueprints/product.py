from flask import Blueprint, jsonify, request, current_app
from sqlalchemy import text, func
from sqlalchemy.orm import joinedload


from ...database import db
from ..decorators import token_required
from ..utils.redis_service import need_product_cache_bucket, cache_products, get_product_cache, get_filtered_products_cache, cache_filtered_products
from ..models import Product, Category, Portion, Role, Portion_Size

from ..utils.aws_s3 import s3_photo_upload

product_bp = Blueprint('product', __name__)


@product_bp.route('/', methods = ['GET'])
def product_index () :
    '''
    Retrieves a paginated list of products with optional filters for category, 
    search term, and sorting. Products with no portions in stock are pushed to the 
    bottom of the list.

    Query Parameters :
    - page (int) : The page number for pagination (default is 1).
    - category (str) : category to filter products by.
    - search (str) : search term to filter products by name.
    - sort (str) : sorting option ('priceAsc', 'priceDesc', 'nameAsc', 'nameDesc').

    Returns :
    - JSON response containing the list of product dictionaries, total pages, and current page.
    - On error, returns a 500 status with an error message.
    '''
    try :
        if need_product_cache_bucket() :
            products = Product.query.all()
            cache_products(products)

        # extract page and params
        page = request.args.get('page', 1, type = int)
        category = request.args.get('category')
        search = request.args.get('search')
        sort = request.args.get('sort')

        cache_key = f'filter:products:{page}:{category}:{search}:{sort}'

        cached_products = get_filtered_products_cache(cache_key)

        if cached_products :
            return jsonify(
                cached_products
            ), 200

        # base query to build upon based on params 
        base_query = Product.query

        if category :
            # adding cateogry filter to query, use uppercase for enum
            base_query = base_query.filter_by(category = Category[category.upper()])

        if sort and sort != 'recommended':
            # to map sort options, utilizing text() in query
            sort_options = {
                'priceAsc': 
                    '''
                        COALESCE(
                            (SELECT price FROM portions
                            WHERE portions.product_id = products.id
                            AND portions.size = :whole
                            LIMIT 1), 0
                        ) ASC
                    '''
                ,
                'priceDesc':
                    '''
                        COALESCE(
                            (SELECT price FROM portions
                            WHERE portions.product_id = products.id
                            AND portions.size = :whole
                            LIMIT 1), 0
                        ) DESC
                    '''
                ,
                'nameAsc': 'name ASC',
                'nameDesc': 'name DESC',
            }
        
            sort_option = sort_options.get(sort)

            if sort_option and sort in ['priceAsc', 'priceDesc'] :
                # adding sort to query
                base_query = base_query.order_by(text(sort_option).params(whole = Portion_Size.WHOLE.value))
            elif sort_option :
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
            response = {
                'products': products_list,
                'totalPages': products.pages,
                'currentPage': page
            }

            cache_filtered_products(cache_key, response)
            
            return jsonify(response), 200
        
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
@token_required
def create_product () :
    '''
    Creates a new product along with its associated portions.

    Request Body :
    - JSON containing the product details : 'name', 'description', 'category', 'image'.
    - JSON containing the price details for the portions.

    Returns :
    - JSON response containing the created product details and a success message.
    - On authentication failure, returns a 401 status with an error message.
    - On error, returns a 500 status with an error message.
    '''
    try :
        admin = request.admin
            
        if admin.role != Role.SUPER :
            return jsonify({
                'error': 'Forbidden'
            }), 403
            
        data = request.form

        if 'image' not in request.files:
            return jsonify({
                'error': 'No image file found in request'
            }), 400

        product_data = {
            key: data.get(key) for key in ['name', 'description', 'category']
        }

        new_product = Product(**product_data)
        db.session.add(new_product)
        db.session.flush()

        portions = new_product.create_portions(data.get('price'))
        db.session.bulk_save_objects(portions)

        file = request.files.get('image')
        image_url = s3_photo_upload(file, str(new_product.id))
        new_product.update_attributes({ 'image': image_url })

        db.session.commit()

        return jsonify({
            'product': new_product.as_dict(),
            'message': 'Product created successfully'
        }), 201
    
    except Exception as error :
        db.session.rollback()
        current_app.logger.error(f'Error creating product: {str(error)}')
        return jsonify({
            'error': error
        }), 500
    

@product_bp.route('/<int:id>/update', methods = ['PUT'])
@token_required
def product_update (id) :
    '''
    Updates the attributes of an existing product.

    Request Body :
    - JSON containing the updated product attributes.

    Returns :
    - JSON response containing the updated product details and a success message.
    - On authentication failure, returns a 401 status with an error message.
    - On product not found, returns a 404 status with an error message.
    - On error, returns a 500 status with an error message.
    '''
    try :
        admin = request.admin
    
        if admin.role == Role.GENERAL :
            return jsonify({
                'error': 'Forbidden'
        }), 403
        
        product = Product.query.get(id)

        if not product :
            return jsonify({
                'error': 'Product not found'
            }), 404
        
        data = { key : value for (key, value) in request.form.items() if key != 'portions' }

        if 'image' in request.files :
            file = request.files.get('image')
            image_url = s3_photo_upload(file, str(product.id))
            data['image'] = image_url

        product.update_attributes(data)
        db.session.commit()

        return jsonify({
            'product': product.as_dict(),
            'message': 'Product updated successfully'
        }), 200

    except Exception as error :
        current_app.logger.error(f'Error updating product: {str(error)}')
        return jsonify({
            'error': error
        }), 500


@product_bp.route('/inventory/generate-report', methods = ['GET'])
@token_required
def product_generate_inventory_report () :
    '''
    Generates a report of products that need inventory restocking based on 
    portion stock levels.

    Returns :
    - JSON response containing a list of products with low stock and the portions 
      that need restocking.
    - JSON response with an updatedPortionsState structure for frontend updates.
    - On authentication failure, returns a 401 status with an error message.
    - On error, returns a 500 status with an error message.
    '''
    try :
        # retrieve token and auth user
        admin = request.admin
        
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
@token_required
def product_update_inventory () :
    '''
    Updates the stock of portions for multiple products based on the input data.

    Request Body :
    - JSON containing the product IDs, portion IDs, and the new stock values.

    Returns :
    - JSON response with a success message when the inventory is updated successfully.
    - On authentication failure, returns a 401 status with an error message.
    - On error, returns a 500 status with an error message.
    '''
    try :
        admin = request.admin

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
                            portion.update_stock(portion.stock + int(new_stock))
                        
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
    '''
    Retrieves the details of a specific product by its ID.

    Returns :
    - JSON response containing the product details.
    - On product not found, returns a 404 status with an error message.
    - On error, returns a 500 status with an error message.
    '''
    try :
        product = get_product_cache(id)

        if not product :
            product = Product.query.get(id)
            if product :
                product = product.as_dict()

        if not product :
            return jsonify({
                'error': 'Product not found'
            }), 404

        return jsonify({
            'product': product
        }), 200
        

    except Exception as error :
        current_app.logger.error(f'Error fetching product: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500