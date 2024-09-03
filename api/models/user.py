import bcrypt
from sqlalchemy import CheckConstraint
from datetime import datetime, timezone

from ...database import db


class User (db.Model) :
    '''
    Represents a user.

    Attributes :
        id (int) : unique identifier for the user.
        name (str) : name of the user.
        email (str) : email address of the user.
        password (str) : hashed password for user's account.
        email_verified (bool) : indicates whether user's email has been verified.
        created_at (datetime) : timestamp when the user was created.
        addresses (relationship) : dynamic relationship to the user's addresses.
    '''
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(30), nullable = False)
    email = db.Column(db.String(256), unique = True, nullable = False)
    password = db.Column(db.LargeBinary, nullable = False)
    email_verified = db.Column(db.Boolean(), default = False, nullable = False)
    created_at = db.Column(db.TIMESTAMP(), nullable = False)

    __table_args__ = (
        # uses regex to ensure email input is in email format
        CheckConstraint(
            "email ~* '^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$'",
            name = 'email_check'
        ),
    )

    # define relationship
    addresses = db.relationship('Address', backref = 'user', lazy = 'dynamic')

    def __init__ (self, name, email, password) :
        '''
        Initializes a new user instance.

        Args :
            name (str) : name of the user.
            email (str) : email address of the user.
            password (str) : plain text password input 
            created_at (datetime) : timestamp when the user was created.
        '''
        self.name = name
        self.email = email
        self.password = self._hash_password(password)
        self.created_at = datetime.now(timezone.utc)


    def _hash_password (self, password) :
        '''
        Hash the password using bcrypt.

        Args :
            password (str) : plain text password input to hash.

        Returns :
            str : the hashed password.
        '''
        return bcrypt.hashpw(str(password).encode(), bcrypt.gensalt())
    
    def verify_password (self, password) :
        '''
        Verify if the provided password matches the stored hashed password.

        Args :
            password (str) : plain text password to verify.

        Returns :
            bool : True if the password matches, False otherwise.
        '''
        return bcrypt.checkpw(str(password).encode(), self.password)
