from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import auth, credentials
import stripe
import os

from .config import config
from .database import init_db

def create_app () : 
    load_dotenv()

    app = Flask(__name__)

    env = os.getenv('FLASK_ENV', 'development')
    app.config.from_object(config[env])

    stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
    webhook_secret = os.getenv('WEBHOOK_SECRET')

    cred = credentials.Certificate(app.config['FIREBASE_CREDENTIALS'])
    firebase_admin.initialize_app(cred)

    CORS(app, supports_credentials = True, origins = '*')
    
    init_db(app)

    from .api.blueprints.product import product_bp
    from .api.blueprints.user import user_bp
    from .api.blueprints.admin import admin_bp
    from .api.blueprints.cart_item import cart_item_bp
    from .api.blueprints.order import order_bp
    from .api.blueprints.address import address_bp

    app.register_blueprint(product_bp, url_prefix='/api/product')
    app.register_blueprint(user_bp, url_prefix='/api/user')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(cart_item_bp, url_prefix = '/api/cart')
    app.register_blueprint(order_bp, url_prefix = '/api/order')
    app.register_blueprint(address_bp, url_prefix = '/api/address')

    @app.after_request
    def after_request(response) :
        response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, OPTIONS, DELETE'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return response

    @app.route('/')
    def home () :
        return 'Hello World!'
    
    return app

if __name__ == '__main__' :
    app = create_app()
    app.run(debug = True)
