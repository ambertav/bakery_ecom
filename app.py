from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import stripe
import os

from .config import config
from .database import init_db
from .redis_config import init_redis, get_redis_client

def create_app () : 
    '''
    Creates and configures the Flask application.

    Sets up the app, loads environment variables, configures third-party services
    (Stripe), and registers blueprints.
    
    Returns :
        Flask: configured Flask app instance.
    '''

    load_dotenv()

    app = Flask(__name__)

    env = os.getenv('FLASK_ENV', 'development')
    app.config.from_object(config[env])

    # initiailize stripe and secret API key
    stripe.api_key = app.config['STRIPE_API_KEY']
    webhook_secret = app.config['WEBHOOK_SECRET']

    # enable CORS
    CORS(app, supports_credentials = True, origins = '*')
    
    init_db(app)
    init_redis(app.config['REDIS_URL'])

    # import blueprints 
    from .api.blueprints.product import product_bp
    from .api.blueprints.user import user_bp
    from .api.blueprints.admin import admin_bp
    from .api.blueprints.cart_item import cart_item_bp
    from .api.blueprints.order import order_bp
    from .api.blueprints.address import address_bp

    # register blueprints
    app.register_blueprint(product_bp, url_prefix = '/api/product')
    app.register_blueprint(user_bp, url_prefix = '/api/user')
    app.register_blueprint(admin_bp, url_prefix = '/api/admin')
    app.register_blueprint(cart_item_bp, url_prefix = '/api/cart')
    app.register_blueprint(order_bp, url_prefix = '/api/order')
    app.register_blueprint(address_bp, url_prefix = '/api/address')

    # apply rate limiter
    @app.before_request
    def global_rate_limit () :
        '''
        Applies a fixed window rate limiter based on client IP address.
        Utilizes `MAX_REQUESTS` and `RATE_LIMIT_WINDOW` values from app configuration.

        Returns :
            Response : 
                - JSON response of 429 error if maximum number of requests is reached in the given window.
                - None if number of requests is within the limit.
        '''
        redis_client = get_redis_client()
        ip = request.remote_addr

        current = redis_client.get(f'rate-limit:{ip}')

        if current :
            current = int(current)
                
            if current >= app.config['MAX_REQUESTS'] :
                return jsonify({
                    'error': 'Too many requests'
                }), 429
                
            redis_client.incr(f'rate-limit:{ip}')
                
        else :
            redis_client.set(f'rate-limit:{ip}', 1, ex = app.config['RATE_LIMIT_WINDOW'])

    @app.after_request
    def after_request(response) :
        '''
        Modifies response headers to support CORS for frontend.

        Args :
            response (Response): the outgoing Flask response object.

        Returns :
            response: modified response object with updated headers.

        '''
        response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, OPTIONS, DELETE'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return response


    # basic test route
    @app.route('/')
    def home () :
        return 'Hello World!'
    
    return app

if __name__ == '__main__' :
    app = create_app()
    app.run(debug = True)
