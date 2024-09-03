import random
import bcrypt
from enum import Enum
from datetime import datetime, timedelta, timezone

from ...database import db

class Role (Enum) :
    SUPER = 'SUPER'
    MANAGER = 'MANAGER'
    GENERAL = 'GENERAL'


class Admin (db.Model) :
    '''
    Represents an admin with secure PIN authentication and expiration management

    Attributes :
        id (int) : unique identifier for the admin.
        employee_id (int) : unique employee identifier.
        email (str) : email address for the admin.
        password (str) : hashed password.
        pin (str) : hashed PIN.
        password_expiration (datetime) : expiration date of the password.
        name (str) : name of the admin.
        role (enum) : role of the admin.
        created_at (datetime) : timestamp for when the admin was created.
        tasks (relationship) : relationship to tasks assigned to the admin.
    '''
    __tablename__ = 'admins'

    id = db.Column(db.Integer, primary_key = True)
    employee_id = db.Column(db.Integer, unique = True, nullable = False)
    email = db.Column(db.String(256), unique = True, nullable = False)
    password = db.Column(db.LargeBinary, nullable = False)
    pin = db.Column(db.LargeBinary, nullable = True, default = None)
    password_expiration = db.Column(db.DateTime(timezone = True), nullable = False)
    name = db.Column(db.String(30), nullable = False)
    role = db.Column(db.Enum(Role), nullable = False)
    created_at = db.Column(db.DateTime(timezone = True), nullable = False)

    tasks = db.relationship('Task', backref = 'admin', lazy = 'dynamic')

    def __init__ (self, name, email, password, pin, role = Role.GENERAL) :
        '''
        Initializes a new admin instance.

        Args :
            name (str) : name of the admin.
            email (str) : email address for the admin.
            password (str) : hashed password.
            pin (str) : the PIN entered.
            role (enum) : role of the admin, default value is GENERAL
        '''
        self.name = name
        self.email = email
        self.password = self._hash_password(password)
        self.pin = self._hash_pin(pin)
        self.role = role
        self.created_at = datetime.now(timezone.utc)

        # generate unique employee id
        self.employee_id = self._generate_unique_employee_id()

        # setting initial password expiration to 90 days after creation
        self.password_expiration = self.created_at + timedelta(days = 90)

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
    
    def _hash_password (self, password) :
        '''
        Hash the password using bcrypt.

        Args :
            password (str) : plain text password input to hash.

        Returns :
            str : the hashed password.
        '''
        return bcrypt.hashpw(str(password).encode(), bcrypt.gensalt()) 

    def _hash_pin (self, pin) :
        '''
        Hash the given PIN using bcrypt.

        Args :
            pin (str) : PIN to be hashed (truncated to 5 digits).

        Returns :
            str : hashed PIN.
        '''
        # ensuring max of 5 digits
        pin = str(pin)[:5]
        return bcrypt.hashpw(pin.encode(), bcrypt.gensalt())

    def verify_password (self, password) :
        '''
        Verify if the provided password matches the stored hashed password.

        Args :
            password (str) : plain text password to verify.

        Returns :
            bool : True if the password matches, False otherwise.
        '''
        return bcrypt.checkpw(str(password).encode(), self.password)
    
    def check_pin (self, pinInput) :
        '''
        Check if given PIN matches stored hashed PIN

        Args :
            pin_input (str) : the PIN to check.
        
        Returns :
            bool : True if the PIN matches, False otherwise.
        '''
        return bcrypt.checkpw(str(pinInput).encode(), self.pin)
    
    def is_password_expired (self) :
        '''
        Check if password has expired.

        Returns :
            bool : True if password is expired, False otherwise.
        '''
        # checking pin expiration
        return datetime.now(timezone.utc) > self.password_expiration

    def renew_password (self, old_password, new_password) :
        '''
        Renews the password if old password is correct.

        Args :
            old_password (str) : the old password to verify.
            new_password (str) : the new password to set.

        Returns :
            bool : True if the password was successfully renewed, False otherwise.
        '''
        if self.verify_password(old_password) :
            # renew password and reset password expiration date (90 days from current time)
            self.password = self._hash_password(new_password)
            self.password_expiration = datetime.now(timezone.utc) + timedelta(days = 90)
            
            return True
        else :
            return False