import os

class Config :
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
    STRIPE_API_KEY = os.getenv('STRIPE_SECRET_KEY')
    WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET')
    REDIS_URL = os.getenv('REDIS_URL')
    MAX_REQUESTS = 60
    RATE_LIMIT_WINDOW = 60

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
}
