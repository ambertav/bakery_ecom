from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import text
from dotenv import load_dotenv
import pyrebase
import os

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')


firebase_config = {
    'apiKey': os.getenv('FIREBASE_API_KEY'),
    'authDomain': "bakery-434c0.firebaseapp.com",
    'projectId': "bakery-434c0",
    'storageBucket': "bakery-434c0.appspot.com",
    'messagingSenderId': "289170495122",
    'appId': "1:289170495122:web:f0b390461c25223041784b",
    'measurementId': "G-B3JJH6BLBW"
}

firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()

db = SQLAlchemy(app)
migrate = Migrate(app, db)


from .blueprints.product import product_bp
from .blueprints.user import user_bp
app.register_blueprint(product_bp, url_prefix = '/product')
app.register_blueprint(user_bp, url_prefix = '/user')


@app.route('/')
def home () :
    return 'Hello World!'



if __name__ == '__main__' :
    app.run(debug=True)