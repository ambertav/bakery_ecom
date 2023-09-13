from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import text
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"

db = SQLAlchemy(app)
migrate = Migrate(app, db)

from .models import Product


@app.route('/')
def home() :
    return 'Hello World!'


@app.route('/add_product')
def add_product() :
    try :
        new_product = Product(
            name = 'test',
            description = 'testing connection and model',
            image = 'test.url',
            price = 99.99,
            stock = 100,
        )

        db.session.add(new_product)
        db.session.commit()

        return jsonify({
            'message' : 'Product created'
        })
    except Exception as error :
        app.logger.error(f'Error creating product: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500



if __name__ == '__main__' :
    app.run(debug=True)