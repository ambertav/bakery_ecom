from flask import Flask, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from sqlalchemy import text
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import auth, credentials
import stripe
import os

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')


cred = credentials.Certificate('/Users/ambertaveras/projects-seirfx/bakery_ecom/backend/bakery-434c0-firebase-adminsdk-6ava5-1a23618776.json')
firebase_admin.initialize_app(cred)

CORS(app, supports_credentials = True, origins='http://localhost:3000')
db = SQLAlchemy(app)
migrate = Migrate(app, db)


from .blueprints.product import product_bp
from .blueprints.user import user_bp
app.register_blueprint(product_bp, url_prefix = '/product')
app.register_blueprint(user_bp, url_prefix = '/user')

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


@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session() :
    cart = request.json.get('cart')

    # dynamically create line_items for stripe checkout session from cart information
    line_items = []
    for item in cart :
        line_item = {
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': item['name'],
                },
                'unit_amount': int(float(item['price']) * 100), # convert price to cents
            },
            'quantity': int(item['quantity']),
        }
        line_items.append(line_item)

    try :
        # create stripe checkout session
        session = stripe.checkout.Session.create(
            line_items = line_items,
            mode = 'payment',
            success_url='http://localhost:4242/success',
            cancel_url='http://localhost:3000/cart',
        )

        return jsonify({
            'checkout_url': session.url
        })
    
    except Exception as error :
        app.logger.error(f'Error: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500


if __name__ == '__main__' :
    app.run(debug=True)