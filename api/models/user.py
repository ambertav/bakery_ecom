from ...database import db

class User (db.Model) :
    '''
    Represents a user.

    Attributes :
        id (int) : unique identifier for the user.
        name (str) : name of the user.
        firebase_uid (str) : unique Firebase user identifier for authentication.
        created_at (datetime) : timestamp when the user was created.
        addresses (relationship) : dynamic relationship to the user's addresses.
    '''
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(30), nullable = False)
    firebase_uid = db.Column(db.String(128), nullable = False)
    created_at = db.Column(db.TIMESTAMP(), nullable = False)

    # define relationship
    addresses = db.relationship('Address', backref = 'user', lazy = 'dynamic')

    def __init__ (self, name, firebase_uid, created_at) :
        '''
        Initializes a new user instance.

        Args :
            name (str) : name of the user.
            firebase_uid (str) : unique Firebase user identifier for authentication.
            created_at (datetime) : timestamp when the user was created.
        '''
        self.name = name
        self.firebase_uid = firebase_uid
        self.created_at = created_at