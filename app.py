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

load_dotenv()

app = Flask(__name__)

env = os.getenv('FLASK_ENV', 'development')
app.config.from_object(config[env])

stripe.api_key = app.config['STRIPE_API_KEY']
webhook_secret = app.config['WEBHOOK_SECRET']

cred = credentials.Certificate(app.config['FIREBASE_CREDENTIALS'])
firebase_admin.initialize_app(cred)

CORS(app, supports_credentials=True, origins='http://localhost:3000')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

from .blueprints.product import product_bp
from .blueprints.user import user_bp
from .blueprints.cart_item import cart_item_bp
from .blueprints.order import order_bp
from .blueprints.address import address_bp

app.register_blueprint(product_bp, url_prefix='/api/product')
app.register_blueprint(user_bp, url_prefix='/api/user')
app.register_blueprint(cart_item_bp, url_prefix = '/api/cart')
app.register_blueprint(order_bp, url_prefix = '/api/order')
app.register_blueprint(address_bp, url_prefix = '/api/address')

@app.after_request
def after_request(response) :
    response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response

@app.route('/')
def home () :
    return 'Hello World!'


if __name__ == '__main__' :
    app.run(debug=True)