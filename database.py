from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# initialize SQLAlchemy and Flask-Migrate instances
db = SQLAlchemy()
migrate = Migrate()

def init_db (app) :
    '''
    Initializes database and migration engine.

    Binds SQLAlchemy and Flask-Migrate instances to the Flask app, allowing
    app to interact with database and handle migrations.

    Args :
        app (Flask) : Flask application instance to which to bind
    '''
    
    db.init_app(app)
    migrate.init_app(app, db)