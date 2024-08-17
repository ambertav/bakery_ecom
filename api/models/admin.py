import random
import bcrypt
from datetime import datetime, timedelta, timezone

from ...database import db


class Admin (db.Model) :
    '''
    Represents an admin with secure PIN authentication and expiration management

    Attributes :
        id (int) : unique identifier for the admin.
        employee_id (int) : unique employee identifier.
        pin (str) : hashed PIN.
        pin_expiration (datetime) : expiration date of the PIN.
        name (str) : name of the admin.
        firebase_uid (str) : Firebase unique identifier.
        created_at (datetime) : timestamp for when the admin was created.
        tasks (relationship) : relationship to tasks assigned to the admin.
    '''
    __tablename__ = 'admins'

    id = db.Column(db.Integer, primary_key = True)
    employee_id = db.Column(db.Integer, unique = True, nullable = False)
    pin = db.Column(db.String(72), nullable = False)
    pin_expiration = db.Column(db.DateTime(timezone = True), nullable = False)
    name = db.Column(db.String(30), nullable = False)
    firebase_uid = db.Column(db.String(128), nullable = False)
    created_at = db.Column(db.DateTime(timezone = True), nullable = False)

    tasks = db.relationship('Task', backref = 'admin', lazy = 'dynamic')

    def __init__ (self, pin, name, firebase_uid, created_at) :
        '''
        Initializes a new admin instance.

        Args :
            pin (str) : the PIN entered.
            name (str) : name of the admin.
            firebase_uid (str) : Firebase unique identifier.
            created_at (datetime) : timestamp for when the admin was created.
        '''
        self.pin = self.hash_pin(pin) # store hash of pin
        self.name = name
        self.firebase_uid = firebase_uid
        self.created_at = created_at

        # generate unique employee id
        self.employee_id = self._generate_unique_employee_id()

        # setting initial pin expiration to 30 days after creation
        self.pin_expiration = self.created_at + timedelta(days = 30)

    def _generate_unique_employee_id (self) :
        '''
        Generates a unique employee ID.

        Ensures that generated ID does not already exist in database.

        Returns :
            int : a unique 8-digit employee ID.
        '''
        # generating random 8 digit number
        id = random.randint(10000000, 99999999)
        
        # checking if employee_id already exists in database
        while Admin.query.filter_by(employee_id = id).first() :
            id = random.randint(10000000, 99999999)
        
        return id
    
    def hash_pin (self, pin) :
        '''
        Hashes the given PIN using bcrypt.

        Args :
            pin (str) : PIN to be hashed (truncated to 5 digits).

        Returns :
            str : hashed PIN.
        '''
        # ensuring max of 5 digits
        pin = str(pin)[:5]

        # generate salt and return hash
        salt = bcrypt.gensalt(12)
        return bcrypt.hashpw(pin.encode(), salt)
    
    def check_pin (self, pinInput) :
        '''
        Checks if given PIN matches stored hashed PIN

        Args :
            pin_input (str) : the PIN to check.
        
        Returns :
            bool : True if the PIN matches, False otherwise.
        '''
        return bcrypt.checkpw(str(pinInput).encode(), self.pin)
    
    def is_pin_expired (self) :
        '''
        Checks if PIN has expired.

        Returns :
            bool : True if PIN is expired, False otherwise.
        '''
        # checking pin expiration
        return datetime.now(timezone.utc) > self.pin_expiration

    def renew_pin (self, old_pin, new_pin) :
        '''
        Renews the PIN if old PIN is correct.

        Args :
            old_pin (str) : the old PIN to verify.
            new_pin (str) : the new PIN to set.

        Returns :
            bool : True if teh PIN was successfully renewed, False otherwise.
        '''
        if bcrypt.checkpw(str(old_pin).encode(), self.pin) :
            # renew pin and reset pin expiration date (30 days from current time)
            self.pin = self.hash_pin(new_pin)
            self.pin_expiration = datetime.now(timezone.utc) + timedelta(days = 30)
            
            return True
        else :
            return False