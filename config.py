import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
    FIREBASE_CREDENTIALS = {
        "type": "service_account",
        "project_id": "bakery-434c0",
        "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID'),
        "private_key": os.getenv('FIREBASE_PRIVATE_KEY'),
        "client_email": "firebase-adminsdk-6ava5@bakery-434c0.iam.gserviceaccount.com",
        "client_id": os.getenv('FIREBASE_CLIENT_ID'),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-6ava5%40bakery-434c0.iam.gserviceaccount.com",
        "universe_domain": "googleapis.com"
    }
    STRIPE_API_KEY = os.getenv('STRIPE_SECRET_KEY')
    WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET')

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
}
